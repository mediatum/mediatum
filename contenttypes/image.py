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
from core import config
from PIL import Image as PILImage, ImageDraw
import core.acl as acl
import logging
import random
import os
from . import default
import hashlib

from schema.schema import VIEW_HIDE_EMPTY
from core.acl import AccessData
from core.attachment import filebrowser
from utils.fileutils import getImportDir
from utils.utils import splitfilename, isnewer, iso2utf8, OperationException, utf8_decode_escape
from core.tree import FileNode
from core.translation import lang, t
from core.styles import getContentStyles
from web.frontend import zoom

""" make thumbnail (jpeg 128x128) """


logg = logging.getLogger(__name__)


def makeThumbNail(image, thumb):
    if isnewer(thumb, image):
        return
    pic = PILImage.open(image)
    tmpjpg = config.get("paths.datadir") + "tmp/img" + ustr(random.random()) + ".jpg"

    if pic.mode == "CMYK" and (image.endswith("jpg") or image.endswith("jpeg")) or pic.mode in ["P", "L"]:
        os.system("convert -quality 100 -draw \"rectangle 0,0 1,1\" %s %s" % (image, tmpjpg))  # always get a rgb image
        pic = PILImage.open(tmpjpg)

    try:
        pic.load()
    except IOError as e:
        pic = None
        raise OperationException("error:" + ustr(e))

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
    im.save(thumb, "jpeg")
    if os.path.exists(tmpjpg):
        os.unlink(tmpjpg)

""" make presentation format (png) """


def makePresentationFormat(image, thumb):
    if isnewer(thumb, image):
        return
    pic = PILImage.open(image)
    tmpjpg = config.get("paths.datadir") + "tmp/img" + ustr(random.random()) + ".jpg"
    if pic.mode == "CMYK" and (image.endswith("jpg") or image.endswith("jpeg")) or pic.mode in ["P", "L"]:
        os.system("convert -quality 100 -draw \"rectangle 0,0 1,1\" %s %s" % (image, tmpjpg))
        pic = PILImage.open(tmpjpg)

    try:
        pic.load()
    except IOError as e:
        logg.exception("exception in makePresentationFormat")
        pic = None
        raise OperationException("error:" + ustr(e))

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
        pic.save(thumb, "jpeg")
    except IOError:
        pic.convert('RGB').save(thumb, "jpeg")

    if os.path.exists(tmpjpg):
        os.unlink(tmpjpg)

""" make original (png real size) """


def makeOriginalFormat(image, thumb):

    tmpjpg = config.get("paths.datadir") + "tmp/img" + ustr(random.random()) + ".jpg"
    pic = PILImage.open(image)
    if pic.mode == "CMYK" and (image.endswith("jpg") or image.endswith("jpeg")) or pic.mode in ["P", "L"]:
        # if image.endswith("jpg") or image.endswith("jpeg"):
        os.system("convert -quality 100 -draw \"rectangle 0,0 1,1\" %s %s" % (image, tmpjpg))
        pic = PILImage.open(tmpjpg)

    try:
        pic.load()
    except IOError as e:
        pic = None
        raise OperationException("error:" + ustr(e))

    pic.save(thumb, "png")
    if os.path.exists(tmpjpg):
        os.unlink(tmpjpg)


""" evaluate image dimensions for given file """


def getImageDimensions(image):
    pic = PILImage.open(image)
    width = pic.size[0]
    height = pic.size[1]
    return width, height


def getJpegSection(image, section):  # section character
    data = ""
    try:
        with open(image, "rb") as fin:
            done = False
            capture = False

            while not done:
                c = fin.read(1)
                if capture and ord(c) != 0xFF and ord(c) != section:
                    data += c

                if ord(c) == 0xFF:  # found tag start
                    if capture:
                        done = True

                    c = fin.read(1)
                    if ord(c) == section:  # found tag
                        capture = True
    except:
        logg.exception("exception in getJpegSection")
        data = ""
    return data


def dozoom(self):
    b = 0
    svg = 0
    for file in self.getFiles():
        if file.getType() == "zoom":
            b = 1
        if file.getName().lower().endswith('svg') and file.type == "original":
            svg = 1
    if self.get("width") and self.get("height") and (int(self.get("width")) > 2000 or int(self.get("height")) > 2000) and not svg:
        b = 1
    return b


""" image class for internal image-type """


class Image(default.Default):

    def getTypeAlias(self):
        return "image"

    def getOriginalTypeName(self):
        return "original"

    def getCategoryName(self):
        return "image"

    # prepare hash table with values for TAL-template
    def _prepareData(self, req):
        mask = self.getFullView(lang(req))

        tif = ""
        try:
            tifs = req.session["fullresolutionfiles"]
        except:
            tifs = []

        access = acl.AccessData(req)
        if access.hasAccess(self, "data"):
            for f in self.getFiles():
                if f.getType() == "original":
                    if self.get('system.origname') == "1":
                        tif = self.getName()
                    else:
                        tif = f.getName()

            if self.get("archive_path") != "":
                tif = "file/" + ustr(self.id) + "/" + self.get("archive_path")

        files, sum_size = filebrowser(self, req)

        obj = {'deleted': False, 'access': access}
        node = self
        if self.get('deleted') == 'true':
            node = self.getActiveVersion()
            obj['deleted'] = True
        obj['path'] = req and req.params.get("path", "") or ""
        obj['attachment'] = files
        obj['sum_size'] = sum_size
        obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY)  # hide empty elements
        obj['node'] = node
        obj['tif'] = tif
        obj['zoom'] = dozoom(node)
        obj['tileurl'] = u"/tile/{}/".format(node.id)
        obj['canseeoriginal'] = access.hasAccess(node, "data")
        obj['originallink'] = u"getArchivedItem('{}/{}')".format(node.id, tif)
        obj['archive'] = node.get('archive_type')

        if "style" in req.params.keys():
            req.session["full_style"] = req.params.get("style", "full_standard")
        elif "full_style" not in req.session.keys():
            if "contentarea" in req.session.keys():
                col = req.session["contentarea"].collection
                req.session["full_style"] = col.get("style_full")
            else:
                req.session["full_style"] = "full_standard"

        obj['style'] = req.session["full_style"]
        return obj

    """ format big view with standard template """
    def show_node_big(self, req, template="", macro=""):
        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()
        return req.getTAL(template, self._prepareData(req), macro)

    def isContainer(self):
        return 0

    def getLabel(self):
        return self.name

    def getSysFiles(self):
        return ["original", "thumb", "presentati", "image", "presentation", "zoom"]

    """ make a copy of the svg file in png format """
    def svg_to_png(self, filename, imgfile):
        # convert svg to png (imagemagick + ghostview)
        os.system("convert -alpha off -colorspace RGB %s -background white %s" % (filename, imgfile))

    """ postprocess method for object type 'image'. called after object creation """
    def event_files_changed(self):
        logg.debug("Postprocessing node %s", self.id)
        if "image" in self.type:
            for f in self.getFiles():
                if f.getName().lower().endswith('svg'):
                    self.svg_to_png(f.retrieveFile(), f.retrieveFile()[:-4] + ".png")
                    self.removeFile(f)
                    self.addFile(FileNode(name=f.retrieveFile(), type="original", mimetype=f.mimetype))
                    self.addFile(FileNode(name=f.retrieveFile(), type="image", mimetype=f.mimetype))
                    self.addFile(FileNode(name=f.retrieveFile()[:-4] + ".png", type="tmppng", mimetype="image/png"))
                    break
            orig = 0
            thumb = 0
            for f in self.getFiles():
                if f.type == "original":
                    orig = 1
                if f.type == "thumb":
                    thumb = 1
            if orig == 0:
                for f in self.getFiles():
                    if f.type == "image":
                        if f.mimetype == "image/tiff" or ((f.mimetype is None or f.mimetype == "application/x-download")
                                                          and (f.getName().lower().endswith("tif") or f.getName().lower().endswith("tiff"))):
                            # move old file to "original", create a new png to be used as "image"
                            self.removeFile(f)

                            path, ext = splitfilename(f.retrieveFile())
                            pngname = path + ".png"
                            if not os.path.isfile(pngname):
                                makeOriginalFormat(f.retrieveFile(), pngname)

                                width, height = getImageDimensions(pngname)
                                self.set("width", width)
                                self.set("height", height)

                            else:
                                width, height = getImageDimensions(pngname)
                                self.set("width", width)
                                self.set("height", height)

                            self.addFile(FileNode(name=pngname, type="image", mimetype="image/png"))
                            self.addFile(FileNode(name=f.retrieveFile(), type="original", mimetype="image/tiff"))
                            break
                        else:
                            self.addFile(FileNode(name=f.retrieveFile(), type="original", mimetype=f.mimetype))

            # retrieve technical metadata.
            for f in self.getFiles():
                if (f.type == "image" and not f.getName().lower().endswith("svg")) or f.type == "tmppng":
                    width, height = getImageDimensions(f.retrieveFile())
                    self.set("origwidth", width)
                    self.set("origheight", height)
                    self.set("origsize", f.getSize())

                    if f.mimetype == "image/jpeg":
                        self.set("jpg_comment", iso2utf8(getJpegSection(f.retrieveFile(), 0xFE).strip()))

            if thumb == 0:
                for f in self.getFiles():
                    if (f.type == "image" and not f.getName().lower().endswith("svg")) or f.type == "tmppng":
                        path, ext = splitfilename(f.retrieveFile())
                        basename = hashlib.md5(ustr(random.random())).hexdigest()[0:8]

                        #path = os.path.join(getImportDir(),os.path.basename(path))
                        path = os.path.join(getImportDir(), basename)

                        thumbname = path + ".thumb"
                        thumbname2 = path + ".thumb2"

                        assert not os.path.isfile(thumbname)
                        assert not os.path.isfile(thumbname2)
                        width, height = getImageDimensions(f.retrieveFile())
                        makeThumbNail(f.retrieveFile(), thumbname)
                        makePresentationFormat(f.retrieveFile(), thumbname2)
                        if f.mimetype is None:
                            if f.getName().lower().endswith("jpg"):
                                f.mimetype = "image/jpeg"
                            else:
                                f.mimetype = "image/tiff"
                        self.addFile(FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                        self.addFile(FileNode(name=thumbname2, type="presentation", mimetype="image/jpeg"))
                        self.set("width", width)
                        self.set("height", height)

            # Exif
            try:
                from lib.Exif import EXIF
                files = self.getFiles()

                for file in files:
                    if file.type == "original":
                        with open(file.retrieveFile(), 'rb') as f:
                            tags = EXIF.process_file(f)
                            tags.keys().sort()

                        unwanted_tags = self.unwanted_exif_attributes()
                        for k in tags.keys():
                            # don't set unwanted exif attributes
                            if any(tag in k for tag in unwanted_tags):
                                continue
                            if tags[k] != "" and k != "JPEGThumbnail":
                                self.set("exif_" + k.replace(" ", "_"),
                                         utf8_decode_escape(ustr(tags[k])))
                            elif k == "JPEGThumbnail":
                                if tags[k] != "":
                                    self.set("Thumbnail", "True")
                                else:
                                    self.set("Thumbnail", "False")

            except:
                logg.exception("exception get EXIF attributes")

            if dozoom(self) == 1:
                tileok = 0
                for f in self.getFiles():
                    if f.type.startswith("tile"):
                        tileok = 1
                if not tileok and self.get("width") and self.get("height"):
                    zoom.getImage(self.id, 1)

            # iptc
            try:
                from lib.iptc import IPTC
                files = self.getFiles()

                for file in files:
                    if file.type == "original":
                        tags = IPTC.getIPTCValues(file.retrieveFile())
                        tags.keys().sort()
                        for k in tags.keys():
                            # skip unknown iptc tags
                            if 'IPTC_' in k:
                                continue
                            if isinstance(tags[k], list):
                                tags[k] = ', '.join(tags[k])
                            if tags[k] != "":
                                self.set("iptc_" + k.replace(" ", "_"),
                                         utf8_decode_escape(ustr(tags[k])))
            except:
                logg.exception("exception getting IPTC attributes")

            for f in self.getFiles():
                if f.getName().lower().endswith("png") and f.type == "tmppng":
                    self.removeFile(f)
                    break


    def unwanted_exif_attributes(self):
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
                'jpg_comment']

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
                             "origsize": "Dateigr&ouml;&szlig;e"
        },

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
        access = AccessData(req)
        d = {}
        svg = 0
        if (not access.hasAccess(self, "data") and not dozoom(self)) or not access.hasAccess(self, "read"):
            req.write(t(req, "permission_denied"))
            return
        zoom_exists = 0
        for file in self.getFiles():
            if file.getType() == "zoom":
                zoom_exists = 1
            if file.getName().lower().endswith('svg') and file.type == "original":
                svg = 1

        d["svg"] = svg
        d["width"] = self.get("origwidth")
        d["height"] = self.get("origheight")
        d["key"] = req.params.get("id", "")
        # we assume that width==origwidth, height==origheight
        d['flash'] = dozoom(self) and zoom_exists
        d['tileurl'] = "/tile/" + self.id + "/"
        req.writeTAL("contenttypes/image.html", d, macro="imageviewer")

    def popup_thumbbig(self, req):
        access = AccessData(req)

        if (not access.hasAccess(self, "data") and not dozoom(self)) or not access.hasAccess(self, "read"):
            req.write(t(req, "permission_denied"))
            return

        thumbbig = None
        for file in self.getFiles():
            if file.getType() == "thumb2":
                thumbbig = file
                break
        if not thumbbig:
            self.popup_fullsize(req)
        else:
            im = PILImage.open(thumbbig.retrieveFile())
            req.writeTAL("contenttypes/image.html", {"filename": '/file/' + ustr(self.id) + '/' +
                                                     thumbbig.getName(), "width": im.size[0], "height": im.size[1]}, macro="thumbbig")

    def processImage(self, type="", value="", dest=""):
        import os

        img = None
        for file in self.getFiles():
            if file.type == "image":
                img = file
                break

        if img:
            pic = PILImage.open(img.retrieveFile())
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

    def getEditMenuTabs(self):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(self):
        return "view"
