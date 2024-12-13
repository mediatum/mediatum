#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import itertools as _itertools
import logging
import os
import exifread as _exifread
from PIL import Image as PILImage

import core as _core
import contenttypes.data as _contenttypes_data
from core.database.postgres.file import File
from core.attachment import filebrowser
from core.postgres import check_type_arg_with_schema
from utils.utils import isnewer
import lib.iptc.IPTC
from utils.compat import iteritems
import utils.process
from collections import defaultdict
import humanize

logg = logging.getLogger(__name__)

def make_thumbnail_image(src_filepath, dest_filepath):
    if isnewer(dest_filepath, src_filepath):
        return

    with PILImage.open(src_filepath) as pic:
        pic.thumbnail(_contenttypes_data.get_thumbnail_size(*pic.size))
        pic = pic.convert("RGB")
        pic.save(dest_filepath, "JPEG", quality="web_high")


def convert_image(src_filepath, dest_filepath, *options):
    """Create a PNG with filename `dest_filepath` from a file at `src_filepath`
    :param options: additional command line option list passed to convert
    """
    utils.process.check_call(("gm", "convert") + options + (src_filepath, dest_filepath))


@check_type_arg_with_schema
class Image(_contenttypes_data.Content):
    # image formats that should exist for each mimetype of the `original` image
    IMAGE_FORMATS_FOR_MIMETYPE = defaultdict(
        lambda: [u"image/png"], {
        u"image/tiff": [u"image/tiff", u"image/png"],
        u"image/svg+xml": [u"image/svg+xml", u"image/png"],
        u"image/jpeg": [u"image/jpeg"],
        u"image/gif": [u"image/gif"],
        u"image/png": [u"image/png"],
        u"image/bmp": [u"image/bmp"]
    })

    MIMETYPE_FOR_EXTENSION = {
        u"jpg": u"image/jpeg",
        u"jpeg": u"image/jpeg",
        u"png": u"image/png",
        u"tif": u"image/tiff",
        u"tiff": u"image/tiff",
        u"gif": u"image/gif",
        u"svg": u"image/svg+xml",
        u"bmp": u"image/bmp",
    }

    # beware of duplicates!
    EXTENSION_FOR_MIMETYPE = {v:k for k, v in iteritems(MIMETYPE_FOR_EXTENSION)}

    @classmethod
    def get_sys_filetypes(cls):
        return [u"image", u"original", u"thumbnail"]

    @classmethod
    def get_upload_filetype(cls):
        return u"original"

    # compare document.py and
    # core.database.postgres.file.File.ORIGINAL_FILETYPES:
    # [u'document', u'original', u'video', u'audio']
    @property
    def original(self):
        # XXX: this should be one() instead of first(), but we must enforce this unique constraint in the DB first
        return self.files.filter_by(filetype=u"original").first()

    def has_object(self):
        return bool(self.original)

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
    def thumbnail_url(self):
        url = u"/thumbnail/{}".format(self.id)
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
        obj = _contenttypes_data.prepare_node_data(self, req)
        if obj["deleted"]:
            # no more processing needed if this object version has been deleted
            # rendering has been delegated to current version
            return obj

        obj["highres_url"] = None

        obj['data_access'] = self.has_data_access()
        obj['has_original'] = self.has_object()

        image_url = '/image/{}'.format(self.id)
        image_url = self._add_version_tag_to_url(image_url)

        files, sum_size = filebrowser(self, req)

        obj['preferred_image_url'] = self.preferred_image_url
        obj["image_formats"] = self.get_image_formats()
        obj['image_url'] = image_url
        obj['attachment'] = files
        obj['sum_size'] = sum_size
        obj['thumbnail_url'] = self.thumbnail_url
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
        original_file, = _itertools.ifilter(lambda f: f.filetype == u"original", files)

        extension = mimetype_to_generate.split("/")[1]
        newimg_name = os.path.splitext(original_file.abspath)[0] + "." + extension

        assert original_file.abspath != newimg_name

        if original_file.mimetype == u"image/svg+xml":
            convert_options = ["-alpha", "off", "-colorspace", "RGB", "-background", "white"]
        else:
            convert_options = []

        old_file = filter(lambda f: f.filetype == u"image" and f.mimetype == mimetype_to_generate, files)

        if old_file:
            old_file, = old_file
            self.files.remove(old_file)
            old_file.unlink()

        convert_image(original_file.abspath, newimg_name, *convert_options)

        self.files.append(File(newimg_name, u"image", mimetype_to_generate))

    def _check_missing_image_formats(self, files=None):
        if files is None:
            files = self.files.all()

        original_file, = _itertools.ifilter(lambda f: f.filetype == u"original", files)
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

        original_file, = _itertools.ifilter(lambda f: f.filetype == u"original", files)

        for old_img_file in _itertools.ifilter(lambda f: f.filetype == u"image", files):
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

        original_file, = _itertools.ifilter(lambda f: f.filetype == u"original", files)

        if original_file.mimetype == u"image/svg+xml":
            original_file = filter(lambda f: f.filetype == u"image" and f.mimetype == u"image/png", files)
            if original_file:
                original_file, = original_file

        return original_file


    def _generate_thumbnails(self, files=None):
        if files is None:
            files = self.files.all()

        image_file = self._find_processing_file(files)
        path = os.path.splitext(image_file.abspath)[0]

        # XXX: we really should use the correct file ending and find another way of naming
        thumbname = u"{}.thumbnail.jpeg".format(path)

        old_thumb_files = filter(lambda f: f.filetype == u"thumbnail", files)

        # XXX: removing files before the new ones are created is bad, that should happen later (use File.unlink_after_deletion).
        # XXX: But we need better thumbnail naming first.
        for old in old_thumb_files:
            self.files.remove(old)
            old.unlink()

        make_thumbnail_image(image_file.abspath, thumbname)

        self.files.append(File(thumbname, u"thumbnail", u"image/jpeg"))


    def _extract_metadata(self, files=None):
        image_file = self._find_processing_file(files)
        with PILImage.open(image_file.abspath) as pic:
            # XXX: this is a bit redundant...
            width = pic.size[0]
            height = pic.size[1]
        self.set("origwidth", width)
        self.set("origheight", height)
        self.set("origsize", image_file.size)
        self.set("width", width)
        self.set("height", height)

        # Exif
        unwanted_attrs = Image.get_unwanted_exif_attributes()

        with open(image_file.abspath, 'rb') as f:
            tags = _exifread.process_file(f)

        for k, v in tags.iteritems():
            # don't set unwanted exif attributes
            if any(tag in k for tag in unwanted_attrs) or not v:
                continue
            self.set("exif_{}".format(k.replace(" ", "_")), v.printable)

        # IPTC
        iptc_metadata = lib.iptc.IPTC.get_iptc_tags(image_file.abspath)
        if iptc_metadata is not None:
            for k, v in iteritems(iptc_metadata):
                self.set('iptc_' + k, v)

    def event_files_changed(self):
        """postprocess method for object type 'image'. called after object creation"""
        logg.debug("Postprocessing node %s", self.id)
        existing_files = self.files.all()

        if not filter(lambda f: f.filetype == u"original", existing_files):
            # we cannot do anything without an `original` file, stop here
            return

        missing_image_mimetypes = self._check_missing_image_formats(existing_files)

        if missing_image_mimetypes:
            self._generate_image_formats(existing_files, missing_image_mimetypes)

        # _generate_image_formats is allowed to change `image` and `original` images, so
        files = self.files.all()

        # generate both thumbnail sizes if one is missing because they should always display the same
        if not filter(lambda f: f.filetype == u"thumbnail", files):
            self._generate_thumbnails(files)

        # should we skip this sometimes? Do we want to overwrite everything?
        self._extract_metadata(files)

        _core.db.session.commit()

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
