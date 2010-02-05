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
import core
import core.config as config
import Image
import core.tree as tree
import core.users as users
import core.athana as athana
import core.acl as acl
import random
import os
import default
import hashlib

from schema.schema import loadTypesFromDB, VIEW_DATA_ONLY, VIEW_HIDE_EMPTY
from core.acl import AccessData
from utils.fileutils import getImportDir
from utils.utils import splitfilename, isnewer, formatException, iso2utf8, OperationException
from core.tree import Node,FileNode
from core.translation import lang,t
from web.frontend import zoom

""" make thumbnail (jpeg 128x128) """
def makeThumbNail(image, thumb):
    import Image,ImageDraw, ImageChops
    if isnewer(thumb,image):
        return
    print "Creating thumbnail for image ",image
    pic = Image.open(image)

    if pic.mode=="CMYK" and (image.endswith("jpg") or image.endswith("jpeg")) or pic.mode in ["P", "L"]:
        tmpjpg = config.get("paths.datadir")+"tmp/img"+str(random.random())+".jpg"
        retcode = os.system("convert "+image+" -depth 8 -colorspace rgb "+tmpjpg)
        pic = Image.open(tmpjpg)
    
    try:
        pic.load()
    except IOError, e:
        pic = None
        raise OperationException("error:"+str(e))

    width = pic.size[0]
    height = pic.size[1]
    if width > height:
        newwidth = 128
        newheight = height*newwidth/width
    else:
        newheight = 128
        newwidth = width*newheight/height
    pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
    im = Image.new(pic.mode, (128, 128), (255, 255, 255))
    
    x = (128-newwidth)/2
    y = (128-newheight)/2
    im.paste( pic, (x,y,x+newwidth,y+newheight))
    
    draw = ImageDraw.ImageDraw(im)
    draw.line([(0,0),(127,0),(127,127),(0,127),(0,0)], (128,128,128))
    
    im = im.convert("RGB")
    im.save(thumb, "jpeg")

""" make presentation format (png) """
def makePresentationFormat(image, thumb):
    import Image,ImageDraw
    if isnewer(thumb,image):
        return
    print "Creating presentation sized version of image ",image
    
    try:
        pic = Image.open(image)
        pic.load()
        pic = pic.convert("RGB")
    except (IOError, ValueError):
        # happens for some TIF files... FIXME: enhance Python's imagelib
        tmppnm = "/tmp/img"+str(random.random())+".pnm"
        #os.system("tifftopnm "+image+" > "+tmppnm)
        #pic = Image.open(tmppnm)
        #pic.load()
        #os.unlink(tmppnm)
        os.system("convert "+image+" -depth 8 -colorspace rgb "+tmppng)
        pic = Image.open(tmppng)
        pic.load()
        pic = pic.convert("RGB")
        os.unlink(tmppng)

    width = pic.size[0]
    height = pic.size[1]

    resize = 1
    if resize:
        # resize images only if they are actually too big
        if width > height:
            newwidth = 320
            newheight = height*newwidth/width
        else:
            newheight = 320
            newwidth = width*newheight/height
        pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
    pic.save(thumb, "jpeg")

""" make original (png real size) """
def makeOriginalFormat(image, thumb):
    import Image
    
    try:
        pic = Image.open(image)
        pic.load()
        pic = pic.convert("RGB")
    except (IOError, ValueError):
        # happens for some TIF files... FIXME: enhance Python's imagelib
        #tmppnm = "/tmp/img"+str(random.random())+".pnm"
        #os.system("tifftopnm "+image+" > "+tmppnm)
        #pic = Image.open(tmppnm)
        #pic.load()
        #os.unlink(tmppnm)
        tmppng = "/tmp/img"+str(random.random())+".png"
        os.system("convert "+image+" -depth 8 -colorspace rgb "+tmppng)
        pic = Image.open(tmppng)
        pic.load()
        pic = pic.convert("RGB")
        os.unlink(tmppng)

    pic.save(thumb,"png")
                    
""" evaluate image dimensions for given file """
def getImageDimensions(image):
    import Image
    pic = Image.open(image)
    width = pic.size[0]
    height = pic.size[1]
    return width,height
    
def getJpegSection(image, section): # section character
    data = ""
    try:
        fin = open(image, "rb")
        done = False
        capture = False

        while not done:
            c = fin.read(1)
            if capture and ord(c)!=0xFF and ord(c)!=section:
                data += c

            if ord(c)==0xFF: # found tag start
                if capture:
                    done = True
                    
                c = fin.read(1)
                if ord(c)==section: # found tag
                    capture = True
        fin.close()
    except:
        data = ""
    return data


def dozoom(node):
    for file in node.getFiles():
        if file.getType()=="zoom":
            return 1
    return 0
    
    #if node.get("width") and node.get("height") and \
    #   (int(node.get("width"))>1000 or int(node.get("height"))>1000) and \
    #   os.path.isfile(os.path.join(config.basedir,"web/img/zoom.swf")):
    #       #if str(node.id) == "629716":
    #           return 1
    #return 0

""" image class for internal image-type """
class Image(default.Default):

    # prepare hash table with values for TAL-template
    def _prepareData(node, req):
        #tifs
        mask = node.getFullView(lang(req))

        tif = ""
        try: 
            tifs = req.session["fullresolutionfiles"]
        except:
            tifs = []

        access = acl.AccessData(req)       
        if access.hasAccess(node,"data"):
            for f in node.getFiles():
                if f.getType()=="original":
                    if node.get('system.origname')=="1":
                        tif = node.getName()
                    else:
                        tif = f.getName()
        
            if node.get("archive_path")!="":
                tif = "file/"+str(node.id)+node.get("archive_path")

        obj = {}
        obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY) # hide empty elements
        obj['node'] = node
        obj['tif'] = tif
        obj['zoom'] = dozoom(node)
        obj['tileurl'] = "/tile/"+node.id+"/"
        obj['canseeoriginal'] = access.hasAccess(node,"data")
        obj['originallink'] = "getArchivedItem('"+str(node.id)+"/"+tif+"')"
        
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
    def show_node_big(node, req):
        return req.getTAL("contenttypes/image.html", node._prepareData(req), macro="showbig")
    
    """ format node image with standard template """
    def show_node_image(node, language=None):
        return '<img src="/thumbs/'+node.id+'" class="thumbnail" border="0"/>'
    
    def isContainer(node):
        return 0

    def getLabel(node):
        return node.name

    def getSysFiles(node):
        return ["original","thumb","presentati","image"]

    """ postprocess method for object type 'image'. called after object creation """
    def event_files_changed(node):
        print "Postprocessing node",node.id
        if "image" in node.type:
            orig = 0
            thumb = 0
            for f in node.getFiles():
                if f.type == "original":
                    orig = 1
                if f.type == "thumb":
                    thumb = 1
            if orig == 0:
                for f in node.getFiles():
                    if f.type == "image":
                        if f.mimetype=="image/tiff" or ((f.mimetype is None or f.mimetype == "application/x-download") and (f.getName().lower().endswith("tif") or f.getName().lower().endswith("tiff"))):
                            # move old file to "original", create a new png to be used as "image"
                            node.removeFile(f)

                            path,ext = splitfilename(f.retrieveFile())
                            pngname = path+".png"
                            if not os.path.isfile(pngname):
                                makeOriginalFormat(f.retrieveFile(), pngname)
                                
                                width, height = getImageDimensions(pngname)
                                node.set("width", width)
                                node.set("height", height)
                                
                            else:
                                width, height = getImageDimensions(pngname)
                                node.set("width", width)
                                node.set("height", height)
                                print "Found preconverted image",pngname

                            node.addFile(FileNode(name=pngname, type="image", mimetype="image/png"))
                            node.addFile(FileNode(name=f.retrieveFile(), type="original", mimetype="image/tiff"))
                            break
                        else:
                            node.addFile(FileNode(name=f.retrieveFile(), type="original", mimetype=f.mimetype))

            # retrieve technical metadata.
            for f in node.getFiles():
                if f.type == "image":
                    width,height = getImageDimensions(f.retrieveFile())
                    node.set("origwidth", width)
                    node.set("origheight", height)
                    node.set("origsize", f.getSize())
                    
                    if f.mimetype=="image/jpeg":
                        node.set("jpg_comment", iso2utf8(getJpegSection(f.retrieveFile(), 0xFE).strip()))

            if thumb == 0:
                for f in node.getFiles():
                    print "look for image",f.type,"|%s|" % f.retrieveFile()
                    if f.type == "image":
                        path,ext = splitfilename(f.retrieveFile())
                        basename = hashlib.md5(str(random.random())).hexdigest()[0:8]
                       
                        #path = os.path.join(getImportDir(),os.path.basename(path))
                        path = os.path.join(getImportDir(),basename)

                        thumbname = path+".thumb"
                        thumbname2 = path+".thumb2"

                        assert not os.path.isfile(thumbname)
                        assert not os.path.isfile(thumbname2)
                        width,height = getImageDimensions(f.retrieveFile())
                        makeThumbNail(f.retrieveFile(), thumbname)
                        makePresentationFormat(f.retrieveFile(), thumbname2)
                        if f.mimetype is None:
                            if f.getName().lower().endswith("jpg"):
                                f.mimetype = "image/jpeg"
                            else:
                                f.mimetype = "image/tiff"
                        node.addFile(FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                        node.addFile(FileNode(name=thumbname2, type="presentation", mimetype="image/jpeg"))
                        node.set("width", width)
                        node.set("height", height)

            # Exif
            try:
                from lib.Exif import EXIF           
                files = node.getFiles()

                for file in files:
                    if file.type=="original":
                        f = open(file.retrieveFile(), 'rb')
                        tags=EXIF.process_file(f)

                        tags.keys().sort()
                        for k in tags.keys():
                            if tags[k]!="" and k!="JPEGThumbnail":
                                node.set("exif_"+k.replace(" ","_"), tags[k])
                            elif k=="JPEGThumbnail":
                                if tags[k]!="":
                                    node.set("Thumbnail", "True")
                                else:
                                    node.set("Thumbnail", "False")

            except:
                None

            if node.get("width")>=5000 or node.get("height")>=5000:# dozoom(node):
                tileok = 0
                for f in node.getFiles():
                    if f.type.startswith("tile"):
                        tileok = 1
                if not tileok and node.get("width") and node.get("height"):
                    zoom.getImage(node.id, 1)

            # iptc
            try:
                from lib.iptc import IPTC
                files = node.getFiles()

                for file in files:
                    if file.type=="original":
                        tags=IPTC.getIPTCValues(file.retrieveFile())
                        tags.keys().sort()
                        for k in tags.keys():
                            if tags[k]!="":
                                node.set("iptc_"+k.replace(" ","_"), tags[k])
            except:
                None

    """ list with technical attributes for type image """
    def getTechnAttributes(node):
        return {"Standard":{"creator":"Ersteller",
                "creationtime":"Erstelldatum",
                "updateuser":"Update Benutzer",
                "updatetime":"Update Datum",
                "height":"H&ouml;he Thumbnail",
                "width":"Breite Thumbnail",
                "faulty":"Fehlerhaft",
                "workflow":"Workflownummer",
                "workflownode":"Workflow Knoten",
                "origwidth":"Originalbreite",
                "origheight":"Originalh&ouml;he",
                "origsize":"Dateigr&ouml;&szlig;e",
                "R-Index":"rindex",
                "M-Index":"mindex",
                "L-Index":"lindex"},

                "Exif":{"exif_EXIF_ComponentsConfiguration": "EXIF ComponentsConfiguration",
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
 
    """ upload functionallity """
    def upload_form(node, req):
        req.writeTAL("contenttypes/image.html", {"metadatatypes":loadTypesFromDB()}, macro="uploadform")

    """ fullsize popup-window for image node """
    def popup_fullsize(node, req):
        access = AccessData(req)

        if (not access.hasAccess(node, "data") and not dozoom(node)) or not access.hasAccess(node,"read"):
            req.write(t(req, "permission_denied"))
            return

        d = {}
        d["key"] = req.params.get("id", "")
        # we assume that width==origwidth, height==origheight
        d['flash'] = dozoom(node)
        d['tileurl'] = "/tile/"+node.id+"/"
        req.writeTAL("contenttypes/image.html", d, macro="imageviewer")
        
    
    def popup_thumbbig(node, req):
        import Image
        access = AccessData(req)

        if (not access.hasAccess(node, "data") and not dozoom(node)) or not access.hasAccess(node,"read"):
            req.write(t(req, "permission_denied"))
            return
        
        thumbbig = None
        for file in node.getFiles():
            if file.getType()=="thumb2":
                thumbbig = file
                break
        if not thumbbig:
            node.popup_fullsize(req)
        else:
            im = Image.open(thumbbig.retrieveFile())
            req.writeTAL("contenttypes/image.html", {"filename":'/file/'+str(node.id)+'/'+thumbbig.getName(), "width":im.size[0], "height":im.size[1]}, macro="thumbbig")

    def processImage(node, type="", value="", dest=""):
        import Image
        import os

        img = None
        for file in node.getFiles():
            if file.type=="image":
                img = file
                break
        
        if img:
            pic = Image.open(img.retrieveFile())
            pic.load()
            
            if type=="percentage":
                w = pic.size[0]*int(value)/100
                h = pic.size[1]*int(value)/100
                
            if type=="pixels":
                if pic.size[0]>pic.size[1]:
                    w = int(value)
                    h = pic.size[1]*int(value)/pic.size[0]
                else:
                    h = int(value)
                    w = pic.size[0]*int(value)/pic.size[1]
            
            elif type=="standard":
                w, h = value.split("x")
                w = int(w)
                h = int(h)

                if pic.size[0]<pic.size[1]:
                    factor_w = w*1.0/pic.size[0]
                    factor_h = h*1.0/pic.size[1]

                    if pic.size[0]*factor_w<w and pic.size[1]*factor_w<h:
                        w = pic.size[0]*factor_w
                        h = pic.size[1]*factor_w
                    else:
                        w = pic.size[0]*factor_h
                        h = pic.size[1]*factor_h
                else:
                    factor_w = w*1.0/pic.size[0]
                    factor_h = h*1.0/pic.size[1]
                    
                    if pic.size[0]*factor_w<w and pic.size[1]*factor_w<h:
                        w = pic.size[0]*factor_h
                        h = pic.size[1]*factor_h
                    else:
                        w = pic.size[0]*factor_w
                        h = pic.size[1]*factor_w
            
            else: # do nothing but copy image
                w = pic.size[0]
                h = pic.size[1]

            pic = pic.resize((int(w),int(h)), Image.ANTIALIAS)
            if not os.path.isdir(dest):
                os.mkdir(dest)
            pic.save(dest+node.id+".jpg", "jpeg")      
            return 1
        return 0


    def getEditMenuTabs(node):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(node):
        return "view"
        
