#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
import os
import tempfile
from PIL import Image as PILImage, ImageDraw

from core import config, File, db
from core.archive import Archive, get_archive_for_node
from core.attachment import filebrowser
from core.translation import t
from core.transition.postgres import check_type_arg_with_schema
from contenttypes.data import Content, prepare_node_data
from utils.utils import isnewer, iso2utf8, utf8_decode_escape
from utils.compat import iteritems

import lib.iptc.IPTC
from lib.Exif import EXIF
from utils.list import filter_scalar
from utils.compat import iteritems
import utils.process
import zipfile
from contextlib import contextmanager
from StringIO import StringIO
from collections import defaultdict
import humanize
from werkzeug.utils import cached_property



logg = logging.getLogger(__name__)

# XXX: some refactoring has to be done for the next two methods, many similarities ...

def make_thumbnail_image(src_filepath, dest_filepath):
    """make thumbnail (jpeg 128x128)"""

    if isnewer(dest_filepath, src_filepath):
        return

    pic = PILImage.open(src_filepath)
    temp_jpg_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)

    try:
        temp_jpg_file.close()
        tmpjpg = temp_jpg_file.name

        if pic.mode == "CMYK" and (src_filepath.endswith("jpg") or src_filepath.endswith("jpeg")) or pic.mode in ["P", "L"]:
            convert_image(src_filepath, tmpjpg, ["-quality", "100", "-draw", "rectangle 0,0 1,1"])
            pic = PILImage.open(tmpjpg)

        pic.load()
        width = pic.size[0]
        height = pic.size[1]

        if width > height:
            newwidth = 128
            newheight = height * newwidth / width
        else:
            newheight = 128
            newwidth = width * newheight / height

        pic = pic.resize((newwidth, newheight), PILImage.ANTIALIAS)

        try:
            im = PILImage.new(pic.mode, (128, 128), (255, 255, 255))
        except:
            im = PILImage.new("RGB", (128, 128), (255, 255, 255))

        x = (128 - newwidth) / 2
        y = (128 - newheight) / 2
        im.paste(pic, (x, y, x + newwidth, y + newheight))

        draw = ImageDraw.ImageDraw(im)
        draw.line([(0, 0), (127, 0), (127, 127), (0, 127), (0, 0)], (128, 128, 128))

        im = im.convert("RGB")
        im.save(dest_filepath, "jpeg")
    finally:
        os.unlink(tmpjpg)


def make_presentation_image(src_filepath, dest_filepath):

    if isnewer(dest_filepath, src_filepath):
        return

    pic = PILImage.open(src_filepath)
    temp_jpg_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)

    try:
        temp_jpg_file.close()
        tmpjpg = temp_jpg_file.name

        if pic.mode == "CMYK" and (src_filepath.endswith("jpg") or src_filepath.endswith("jpeg")) or pic.mode in ["P", "L"]:
            convert_image(src_filepath, tmpjpg, ["-quality", "100", "-draw", "rectangle 0,0 1,1"])
            pic = PILImage.open(tmpjpg)

        pic.load()

        width = pic.size[0]
        height = pic.size[1]

        resize = 1
        if resize:
            # resize images only if they are actually too big
            if width > height:
                newwidth = 320
                newheight = height * newwidth / width
            else:
                newheight = 320
                newwidth = width * newheight / height
            pic = pic.resize((newwidth, newheight), PILImage.ANTIALIAS)

        try:
            pic.save(dest_filepath, "jpeg")
        except IOError:
            pic.convert('RGB').save(dest_filepath, "jpeg")

    finally:
        os.unlink(tmpjpg)


def convert_image(src_filepath, dest_filepath, options=[]):
    """Create a PNG with filename `dest_filepath` from a file at `src_filepath`
    :param options: additional command line option list passed to convert
    """
    utils.process.check_call(["convert"] + options + [src_filepath, dest_filepath])


def get_image_dimensions(image):
    pic = PILImage.open(image.abspath)
    width = pic.size[0]
    height = pic.size[1]
    return width, height


@contextmanager
def _create_zoom_tile_buffer(img, max_level, tilesize, level, x, y):
    level = 1 << (max_level - level)
    buff = StringIO()

    x0, y0, x1, y1 = (x * tilesize * level, y * tilesize * level, (x + 1) * tilesize * level, (y + 1) * tilesize * level)
    if x0 > img.size[0] or y0 > img.size[1]:
        yield None

    if x1 > img.size[0]:
        x1 = img.size[0]
    if y1 > img.size[1]:
        y1 = img.size[1]

    xl = (x1 - x0) / level
    yl = (y1 - y0) / level

    # do not resize to zero dimension (would cause exception when saving)
    xl = max(1, xl)
    yl = max(1, yl)

    img = img.crop((x0, y0, x1, y1)).resize((xl, yl))
    img.save(buff, format="JPEG")
    try:
        yield buff
    finally:
        buff.close()


def get_zoom_zip_filename(nid):
    return u"zoom{}.zip".format(nid)


def _create_zoom_archive(tilesize, image_filepath, zoom_zip_filepath):
    """Create tiles in zip file that will be displayed by zoom.swf"""
    img = PILImage.open(image_filepath)
    img = img.convert("RGB")

    width, height = img.size
    l = max(width, height)
    max_level = 0
    while l > tilesize:
        l = l / 2
        max_level += 1

    logg.debug('Creating: %s', zoom_zip_filepath)
    with zipfile.ZipFile(zoom_zip_filepath, "w") as zfile:
        for level in range(max_level + 1):
            t = (tilesize << (max_level - level))
            for x in range((width + (t - 1)) / t):
                for y in range((height + (t - 1)) / t):
                    with _create_zoom_tile_buffer(img, max_level, tilesize, level, x, y) as buff:
                        tile_name = "tile-%d-%d-%d.jpg" % (level, x, y)
                        zfile.writestr(tile_name, buff.getvalue(), zipfile.ZIP_DEFLATED)


@check_type_arg_with_schema
class Image(Content):

    #: create zoom tiles when width or height of image exceeds this value
    ZOOM_SIZE = 2000

    ZOOM_TILESIZE = 256

    # image formats that should exist for each mimetype of the `original` image
    IMAGE_FORMATS_FOR_MIMETYPE = defaultdict(
        lambda: [u"image/png"], {
        u"image/tiff": [u"image/tiff", u"image/png"],
        u"image/svg+xml": [u"image/svg+xml", u"image/png"],
        u"image/jpeg": [u"image/jpeg"],
        u"image/gif": [u"image/gif"],
        u"image/png": [u"image/png"]
    })

    MIMETYPE_FOR_EXTENSION = {
        u"jpg": u"image/jpeg",
        u"jpeg": u"image/jpeg",
        u"png": u"image/png",
        u"tif": u"image/tiff",
        u"tiff": u"image/tiff",
        u"gif": u"image/gif",
        u"svg": u"image/svg+xml",
    }

    # beware of duplicates!
    EXTENSION_FOR_MIMETYPE = {v:k for k, v in iteritems(MIMETYPE_FOR_EXTENSION)}

    @classmethod
    def get_default_edit_menu_tabs(cls):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    @classmethod
    def get_sys_filetypes(cls):
        return [u"original", u"thumb", u"image", u"presentation", u"zoom"]

    @classmethod
    def get_upload_filetype(cls):
        return u"original"

    @property
    def svg_image(self):
        return self.files.filter_by(filetype=u"image", mimetype=u"image/svg+xml").scalar()

    @property
    def zoom_available(self):
        zoom_file = self.files.filter_by(filetype=u"zoom").scalar()
        return zoom_file is not None

    @property
    def should_use_zoom(self):
        # svg should never use the flash zoom
        if self.svg_image is not None:
            return False

        return int(self.get("width") or 0) > Image.ZOOM_SIZE or int(self.get("height") or 0) > Image.ZOOM_SIZE

    def image_url_for_mimetype(self, mimetype):
        try:
            file_ext = Image.EXTENSION_FOR_MIMETYPE[mimetype]
        except KeyError:
            raise ValueError("unsupported image mimetype " + mimetype)

        url = u"/image/{}.{}".format(self.id, file_ext)

        return self._add_version_tag_to_url(url)

    @property
    def preferred_image_url(self):
        url = u"/image/" + unicode(self.id)
        return self._add_version_tag_to_url(url)

    @property
    def presentation_url(self):
        url = u"/thumb2/" + unicode(self.id)
        return self._add_version_tag_to_url(url)

    def get_image_formats(self):
        image_files = self.files.filter_by(filetype=u"image")
        image_formats = {}
        for img_file in image_files:
            if img_file.exists:
                image_formats[img_file.mimetype] = {
                    "url": self.image_url_for_mimetype(img_file.mimetype),
                    "display_size": humanize.filesize.naturalsize(img_file.size)
                }

        return image_formats

    # prepare hash table with values for TAL-template
    def _prepareData(self, req):
        obj = prepare_node_data(self, req)
        if obj["deleted"]:
            # no more processing needed if this object version has been deleted
            # rendering has been delegated to current version
            return obj

        obj["highres_url"] = None

        can_see_original = self.has_data_access()

        archive = get_archive_for_node(self)
        if archive:
            if can_see_original:
                obj['highres_url'] = u"/file/{nid}/{nid}.tif".format(nid=self.id)
                archive_state = archive.get_file_state(self)
                if archive_state == Archive.NOT_PRESENT:
                    obj['archive_fetch_url'] = u"/archive/{}".format(self.id)
                elif archive_state == Archive.PRESENT:
                    obj['archive_fetch_url'] = None

        files, sum_size = filebrowser(self, req)

        obj['canseeoriginal'] = can_see_original
        obj['preferred_image_url'] = self.preferred_image_url
        obj["image_formats"] = self.get_image_formats()
        obj['zoom'] = self.zoom_available
        obj['attachment'] = files
        obj['sum_size'] = sum_size
        obj['presentation_url'] = self.presentation_url
        obj['fullsize'] = str(self.id)
        if not self.isActiveVersion():
            obj['tag'] = self.tag
            obj['fullsize'] += "&v=" + self.tag
        obj['fullsize'] = '"' + obj['fullsize'] + '"'

        full_style = req.args.get(u"style", u"full_standard")
        if full_style:
            obj['style'] = full_style

        return obj

    def _generate_other_format(self, mimetype_to_generate, files=None):
        original_file = filter_scalar(lambda f: f.filetype == u"original", files)

        extension = mimetype_to_generate.split("/")[1]
        newimg_name = os.path.splitext(original_file.abspath)[0] + "." + extension

        assert original_file.abspath != newimg_name

        if original_file.mimetype == u"image/svg+xml":
            convert_options = ["-alpha", "off", "-colorspace", "RGB", "-background", "white"]
        else:
            convert_options = []

        old_file = filter_scalar(lambda f: f.filetype == u"image" and f.mimetype == mimetype_to_generate, files)

        if old_file is not None:
            self.files.remove(old_file)
            old_file.unlink()

        convert_image(original_file.abspath, newimg_name, convert_options)

        self.files.append(File(newimg_name, u"image", mimetype_to_generate))

    def _check_missing_image_formats(self, files=None):
        if files is None:
            files = self.files.all()

        original_file = filter_scalar(lambda f: f.filetype == u"original", files)
        old_image_files = filter(lambda f: f.filetype == u"image", files)

        wanted_mimetypes = set(Image.IMAGE_FORMATS_FOR_MIMETYPE[original_file.mimetype])

        return wanted_mimetypes - {f.mimetype for f in old_image_files}

    def _generate_image_formats(self, files=None, mimetypes_to_consider=None):
        """Creates other full size formats for this image node.

        TIFF: create new PNG to be used as `image`
        SVG: create PNG and add it as `png_image`

        :param mimetypes_to_consider: limit the formats that should be (re)-generated to this sequence of mimetypes
        """
        if files is None:
            files = self.files.all()

        original_file = filter_scalar(lambda f: f.filetype == u"original", files)
        old_image_files = filter(lambda f: f.filetype == u"image", files)

        for old_img_file in old_image_files:
            # we don't want to remove the original file...
            if old_img_file.path != original_file.path:
                self.files.remove(old_img_file)
                old_img_file.unlink()

        mimetypes_to_generate = set(Image.IMAGE_FORMATS_FOR_MIMETYPE[original_file.mimetype])

        if mimetypes_to_consider is not None:
            mimetypes_to_generate = mimetypes_to_generate.intersection(mimetypes_to_consider)

        for new_mimetype in mimetypes_to_generate:
            if new_mimetype == original_file.mimetype:
                # image is alias for the original image in this case
                fileobj = File(original_file.path, u"image", original_file.mimetype)
                self.files.append(fileobj)
            else:
                self._generate_other_format(new_mimetype, files)


    def _find_processing_file(self, files=None):
        """Finds the file that should be used for processing (generating thumbnails, extracting metadata etc) in a file sequence.
        """
        if files is None:
            files = self.files.all()

        original_file = filter_scalar(lambda f: f.filetype == u"original", files)

        if original_file.mimetype == u"image/svg+xml":
            return filter_scalar(lambda f: f.filetype == u"image" and f.mimetype == u"image/png", files)

        return original_file


    def _generate_thumbnails(self, files=None):
        if files is None:
            files = self.files.all()

        image_file = self._find_processing_file(files)
        path = os.path.splitext(image_file.abspath)[0]

        # XXX: we really should use the correct file ending and find another way of naming
        thumbname = path + ".thumb"
        thumbname2 = path + ".presentation"

        old_thumb_files = filter(lambda f: f.filetype in (u"thumb", u"presentation"), files)

        # XXX: removing files before the new ones are created is bad, that should happen later (use File.unlink_after_deletion).
        # XXX: But we need better thumbnail naming first.
        for old in old_thumb_files:
            self.files.remove(old)
            old.unlink()

        make_thumbnail_image(image_file.abspath, thumbname)
        make_presentation_image(image_file.abspath, thumbname2)

        self.files.append(File(thumbname, u"thumb", u"image/jpeg"))
        self.files.append(File(thumbname2, u"presentation", u"image/jpeg"))

    def _generate_zoom_archive(self, files=None):
        if files is None:
            files = self.files.all()

        image_file = self._find_processing_file(files)

        zip_filename = get_zoom_zip_filename(self.id)
        zip_filepath = os.path.join(config.get("paths.zoomdir"), zip_filename)

        old_zoom_files = filter(lambda f: f.filetype == u"zoom", files)

        for old in old_zoom_files:
            self.files.remove(old)
            old.unlink()

        _create_zoom_archive(Image.ZOOM_TILESIZE, image_file.abspath, zip_filepath)
        file_obj = File(path=zip_filepath, filetype=u"zoom", mimetype=u"application/zip")
        self.files.append(file_obj)

    def _extract_metadata(self, files=None):
        image_file = self._find_processing_file(files)
        width, height = get_image_dimensions(image_file)
        # XXX: this is a bit redundant...
        self.set("origwidth", width)
        self.set("origheight", height)
        self.set("origsize", image_file.size)
        self.set("width", width)
        self.set("height", height)

        # Exif
        unwanted_attrs = Image.get_unwanted_exif_attributes()

        with open(image_file.abspath, 'rb') as f:
            tags = EXIF.process_file(f)

        for k in tags.keys():
            # don't set unwanted exif attributes
            if any(tag in k for tag in unwanted_attrs):
                continue
            if tags[k]:
                self.set("exif_" + k.replace(" ", "_"), utf8_decode_escape(str(tags[k])))

        # IPTC
        iptc_metadata = lib.iptc.IPTC.get_iptc_tags(image_file.abspath)
        if iptc_metadata is not None:
            for k, v in iteritems(iptc_metadata):
                self.set('iptc_' + k, v)

    def event_files_changed(self):
        """postprocess method for object type 'image'. called after object creation"""
        logg.debug("Postprocessing node %s", self.id)
        existing_files = self.files.all()

        if filter_scalar(lambda f: f.filetype == u"original", existing_files) is None:
            # we cannot do anything without an `original` file, stop here
            return

        missing_image_mimetypes = self._check_missing_image_formats(existing_files)

        if missing_image_mimetypes:
            self._generate_image_formats(existing_files, missing_image_mimetypes)

        # _generate_image_formats is allowed to change `image` and `original` images, so
        files = self.files.all()

        # generate both thumbnail sizes if one is missing because they should always display the same
        if (filter_scalar(lambda f: f.filetype == u"thumb", files) is None
            or filter_scalar(lambda f: f.filetype == u"presentation", files) is None):
            self._generate_thumbnails(files)

        # should we skip this sometimes? Do we want to overwrite everything?
        self._extract_metadata(files)

        if self.should_use_zoom:
            try:
                self._generate_zoom_archive(files)
            except:
                # XXX: this sometimes throws SystemError, see #806
                # XXX: missing zoom tiles shouldn't abort the upload process
                logg.exception("zoom image generation failed!")

        # XXX: IPTC writeback will be fixed in #782
        # self._writeback_iptc()

        db.session.commit()

    @classmethod
    def get_unwanted_exif_attributes(cls):
        '''
        Returns a list of unwanted exif tags which are not to be extracted from uploaded images
        @return: list
        '''
        return ['BitsPerSample',
                'IPTC/NAA',
                'WhitePoint',
                'YCbCrCoefficients',
                'ReferenceBlackWhite',
                'PrimaryChromaticities',
                'ImageDescription',
                'StripOffsets',
                'StripByteCounts',
                'CFAPattern',
                'CFARepeatPatternDim',
                'YCbCrSubSampling',
                'Tag',
                'TIFFThumbnail',
                'JPEGThumbnail',
                'Thumbnail_BitsPerSample',
                'GPS',
                'CVAPattern',
                'ApertureValue',
                'ShutterSpeedValue',
                'MakerNote',
                'jpg_comment',
                'UserComment',
                'FlashPixVersion',
                'ExifVersion',
                'Caption',
                'Byline',
                'notice']

    """ list with technical attributes for type image """
    def getTechnAttributes(self):
        return {"Standard": {"creator": "Ersteller",
                             "creationtime": "Erstelldatum",
                             "updateuser": "Update Benutzer",
                             "updatetime": "Update Datum",
                             "updatesearchindex": "Update Suche",
                             "height": "H&ouml;he Thumbnail",
                             "width": "Breite Thumbnail",
                             "faulty": "Fehlerhaft",
                             "workflow": "Workflownummer",
                             "workflownode": "Workflow Knoten",
                             "origwidth": "Originalbreite",
                             "origheight": "Originalh&ouml;he",
                             "origsize": "Dateigr&ouml;&szlig;e"},

                "Exif": {"exif_EXIF_ComponentsConfiguration": "EXIF ComponentsConfiguration",
                         "exif_EXIF_LightSource": "EXIF LightSource",
                         "exif_EXIF_FlashPixVersion": "EXIF FlashPixVersion",
                         "exif_EXIF_ColorSpace": "EXIF ColorSpace",
                         "exif_EXIF_MeteringMode": "EXIF MeteringMode",
                         "exif_EXIF_ExifVersion": "EXIF ExifVersion",
                         "exif_EXIF_Flash": "EXIF Flash",
                         "exif_EXIF_DateTimeOriginal": "EXIF DateTimeOriginal",
                         "exif_EXIF_InteroperabilityOffset": "EXIF InteroperabilityOffset",
                         "exif_EXIF_FNumber": "EXIF FNumber",
                         "exif_EXIF_FileSource": "EXIF FileSource",
                         "exif_EXIF_ExifImageLength": "EXIF ExifImageLength",
                         "exif_EXIF_SceneType": "EXIF SceneType",
                         "exif_EXIF_CompressedBitsPerPixel": "EXIF CompressedBitsPerPixel",
                         "exif_EXIF_ExposureBiasValue": "EXIF ExposureBiasValue",
                         "exif_EXIF_ExposureProgram": "EXIF ExposureProgram",
                         "exif_EXIF_ExifImageWidth": "EXIF ExifImageWidth",
                         "exif_EXIF_DateTimeDigitized": "EXIF DateTimeDigitized",
                         "exif_EXIF_FocalLength": "EXIF FocalLength",
                         "exif_EXIF_ExposureTime": "EXIF ExposureTime",
                         "exif_EXIF_ISOSpeedRatings": "EXIF ISOSpeedRatings",
                         "exif_EXIF_MaxApertureValue": "EXIF MaxApertureValue",

                         "exif_Image_Model": "Image Model",
                         "exif_Image_Orientation": "Image Orientation",
                         "exif_Image_DateTime": "Image DateTime",
                         "exif_Image_YCbCrPositioning": "Image YCbCrPositioning",
                         "exif_Image_ImageDescription": "Image ImageDescription",
                         "exif_Image_ResolutionUnit": "Image ResolutionUnit",
                         "exif_Image_XResolution": "Image XResolution",
                         "exif_Image_Make": "Image Make",
                         "exif_Image_YResolution": "Image YResolution",
                         "exif_Image_ExifOffset": "Image ExifOffset",

                         "exif_Thumbnail_ResolutionUnit": "Thumbnail ResolutionUnit",
                         "exif_Thumbnail_DateTime": "Thumbnail DateTime",
                         "exif_Thumbnail_JPEGInterchangeFormat": "Thumbnail JPEGInterchangeFormat",
                         "exif_Thumbnail_JPEGInterchangeFormatLength": "Thumbnail JPEGInterchangeFormatLength",
                         "exif_Thumbnail_YResolution": "Thumbnail YResolution",
                         "exif_Thumbnail_Compression": "Thumbnail Compression",
                         "exif_Thumbnail_Make": "Thumbnail Make",
                         "exif_Thumbnail_XResolution": "Thumbnail XResolution",
                         "exif_Thumbnail_Orientation": "Thumbnail Orientation",
                         "exif_Thumbnail_Model": "Thumbnail Model",
                         "exif_JPEGThumbnail": "JPEGThumbnail",
                         "Thumbnail": "Thumbnail"}}

    """ fullsize popup-window for image node """
    def popup_fullsize(self, req):
        # XXX: should be has_data_access instead, see #1135>
        if not self.has_read_access():
            return 404

        no_flash_requested = req.args.get("no_flash", type=int) == 1
        use_flash_zoom = not no_flash_requested and config.getboolean("image.use_flash_zoom", True) and self.should_use_zoom

        if use_flash_zoom and not self.zoom_available:
            logg.warn("missing zoom file for image # %s", self.id, trace=False)

        d = {}
        d["flash"] = use_flash_zoom
        d["svg_url"] = self.image_url_for_mimetype(u"image/svg+xml") if self.svg_image else None
        d["width"] = self.get("width")
        # we assume that width==origwidth, height==origheight
        # XXX: ^ wrong!
        d["height"] = self.get("height")
        d["image_url"] = self.preferred_image_url
        d['tileurl'] = "/tile/{}/".format(self.id)
        if use_flash_zoom:
            d["no_flash_url"] = "/fullsize?id={}&no_flash=1".format(self.id)
        req.writeTAL("contenttypes/image.html", d, macro="imageviewer")

    def popup_thumbbig(self, req):
        self.popup_fullsize(req)

    def processImage(self, type="", value="", dest=""):
        """XXX: this method is only called in shoppingbags.
        What does it even do?!
        """
        img = None
        for file in self.files:
            if file.filetype == "image":
                img = file
                break

        if img:
            pic = PILImage.open(img.abspath)
            pic.load()

            if type == "percentage":
                w = pic.size[0] * int(value) / 100
                h = pic.size[1] * int(value) / 100

            if type == "pixels":
                if pic.size[0] > pic.size[1]:
                    w = int(value)
                    h = pic.size[1] * int(value) / pic.size[0]
                else:
                    h = int(value)
                    w = pic.size[0] * int(value) / pic.size[1]

            elif type == "standard":
                w, h = value.split("x")
                w = int(w)
                h = int(h)

                if pic.size[0] < pic.size[1]:
                    factor_w = w * 1.0 / pic.size[0]
                    factor_h = h * 1.0 / pic.size[1]

                    if pic.size[0] * factor_w < w and pic.size[1] * factor_w < h:
                        w = pic.size[0] * factor_w
                        h = pic.size[1] * factor_w
                    else:
                        w = pic.size[0] * factor_h
                        h = pic.size[1] * factor_h
                else:
                    factor_w = w * 1.0 / pic.size[0]
                    factor_h = h * 1.0 / pic.size[1]

                    if pic.size[0] * factor_w < w and pic.size[1] * factor_w < h:
                        w = pic.size[0] * factor_h
                        h = pic.size[1] * factor_h
                    else:
                        w = pic.size[0] * factor_w
                        h = pic.size[1] * factor_w

            else:  # do nothing but copy image
                w = pic.size[0]
                h = pic.size[1]

            pic = pic.resize((int(w), int(h)), PILImage.ANTIALIAS)
            if not os.path.isdir(dest):
                os.mkdir(dest)
            pic.save(dest + self.id + ".jpg", "jpeg")
            return 1
        return 0

    def event_metadata_changed(self):
        pass
        # XXX: IPTC writeback will be fixed in #782
        # self._writeback_iptc()


    def _writeback_iptc(self):
        """ Handles metadata content if changed.
            Creates a 'new' original [old == upload].
        """
        upload_file = None
        original_path = None
        original_file = None

        for f in self.files:
            if f.getType() == 'original':
                original_file = f
                if os.path.exists(f.abspath):
                    original_path = f.abspath
                if os.path.basename(original_path).startswith('-'):
                    return

            if f.type == 'upload':
                if os.path.exists(f.abspath):
                    upload_file = f

        if not original_file:
            logg.info('No original upload for writing IPTC.')
            return

        if not upload_file:
            upload_path = '{}_upload{}'.format(os.path.splitext(original_path)[0], os.path.splitext(original_path)[-1])
            import shutil
            shutil.copy(original_path, upload_path)
            self.files.append(File(upload_path, "upload", original_file.mimetype))
            db.session.commit()

        tag_dict = {}

        for field in self.getMetaFields():
            if field.get('type') == "meta" and field.getValueList()[0] != '' and 'on' in field.getValueList():
                tag_name = field.getValueList()[0].split('iptc_')[-1]

                field_value = self.get('iptc_{}'.format(field.getName()))

                if field.getValueList()[0] != '' and 'on' in field.getValueList():
                    tag_dict[tag_name] = field_value

        lib.iptc.IPTC.write_iptc_tags(original_path, tag_dict)
