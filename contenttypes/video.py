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
import core.config as config
import core.tree as tree
import core.athana as athana
import core.acl as acl
import os
import Image

from utils.utils import splitfilename, splitpath
from utils.date import format_date, make_date
from core.acl import AccessData
from core.tree import Node,FileNode
from lib.flv.parse import getFLVSize, FLVReader
from contenttypes.image import makeThumbNail,makePresentationFormat
from core.translation import t
from core.styles import getContentStyles
import default

""" video class """
class Video(default.Default):
    def getTypeAlias(node):
        return "video"
        
    def getCategoryName(node):
        return "video"
        
    def _prepareData(node, req, words=""):
        access = acl.AccessData(req)
        mask = node.getMask("nodebig")
        obj = {}
        for filenode in node.getFiles():
            if filenode.getType()=="original" or filenode.getType()=="video":
                obj["file"] =  "/file/" + str(node.id) + "/" + filenode.getName()
                break

        obj['metadata'] = mask.getViewHTML([node], 2) # hide empty elements
        obj['node'] = node  
        obj['path'] = req.params.get("path","")
        obj['canseeoriginal'] = access.hasAccess(node,"data")
        return obj

    """ format big view with standard template """
    def show_node_big(node, req, template="", macro=""):
        if template=="":
            styles = getContentStyles("bigview", contenttype=node.getContentType())
            if len(styles)>=1:
                template = styles[0].getTemplate()
        return req.getTAL(template, node._prepareData(req), macro)

    """ returns preview image """
    def show_node_image(node):
        return '<img src="/thumbs/'+node.id+'" class="thumbnail" border="0"/>'
    
    def event_files_changed(node):
        for f in node.getFiles():
            if f.type == "thumb" or f.type == "presentation":
                node.removeFile(f)
        
        
        for f in node.getFiles():
            if f.type in["original", "video"]:
                if f.mimetype=="video/x-flv":
                    meta = FLVReader(f.retrieveFile())
                    for key in meta:
                        try:
                            node.set(key, int(meta[key]))
                        except:
                            node.set(key, meta[key])
                            
                    node.set("vid-width", node.get("width"))
                    node.set("vid-height", node.get("height"))
                    
                    tempname = os.path.join(config.get("paths.tempdir"),"tmp.gif")
                    try:
                        os.unlink(tempname);
                    except:
                        pass

                    try:
                        if node.get("system.thumbframe")!="":
                            cmd = "ffmpeg -vframes 1 -ss "+node.get("system.thumbframe")+" -i "+f.retrieveFile()+" -pix_fmt rgb24 "+tempname
                        else:
                            cmd = "ffmpeg -vframes 1 -i "+f.retrieveFile()+" -pix_fmt rgb24 "+tempname
                        ret = os.system(cmd)
                        if ret & 0xff00:
                            return
                    except:
                        return
                    path,ext = splitfilename(f.retrieveFile())
                    thumbname = path+".thumb"
                    thumbname2 = path+".thumb2"
                    makeThumbNail(tempname, thumbname)
                    makePresentationFormat(tempname, thumbname2)
                    node.addFile(FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                    node.addFile(FileNode(name=thumbname2, type="presentation", mimetype="image/jpeg"))
     
    def isContainer(node):
        return 0

    def getSysFiles(node):
        return ["presentation", "thumb", "video"]

    def getLabel(node):
        return node.name
        
    def getDuration(node):
        duration = node.get("duration")
        try:
            duration = float(duration)
        except ValueError:
            return 0
        else:
            _s = int(duration % 60)
            _m = duration/60
            _h = int(duration) /3600
            return format_date(make_date(0,0,0,_h,_m,_s), '%H:%M:%S')

    """ list with technical attributes for type video """
    def getTechnAttributes(node):
        return {"Standard":{"creationtime":"Erstelldatum",
                             "creator":"Ersteller"},
                "FLV":{"audiodatarate": "Audio Datenrate",
                        "videodatarate": "Video Datenrate",
                        "framerate": "Frame Rate",
                        "height": "Videoh\xc3\xb6he",
                        "width": "Breite",
                        "audiocodecid": "Audio Codec",
                        "duration": "Dauer",
                        "canSeekToEnd": "Suchbar",
                        "videocodecid": "Video Codec",
                        "audiodelay": "Audioversatz"}
                }

    """ popup window for actual nodetype """
    def popup_fullsize(node, req):
        access = AccessData(req)
        if not access.hasAccess(node, "data") or not access.hasAccess(node,"read"):
            req.write(t(req, "permission_denied"))
            return
    
        f = None
        for filenode in node.getFiles():
            if filenode.getType()=="original" or filenode.getType()=="video":
                f =  "/file/" + str(node.id) + "/" + filenode.getName()
                break

        file = f
        if file:
            script = """<p href=\""""+file+"""\" style="display:block;width:"""+str(int(node.get('vid-width') or '0')+64)+"""px;height:"""+str(int(node.get('vid-height') or '0')+53)+"""px;" id="player"/p>"""
        else:
            script = ""

        req.writeTAL("contenttypes/video.html", {"file":file, "script":script, "node":node, "width":int(node.get('vid-width') or '0')+64, "height":int(node.get('vid-height') or '0')+53}, macro="fullsize_flv")

    def popup_thumbbig(node, req):
        node.popup_fullsize(req)
        
    def getEditMenuTabs(node):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"
        
    def getDefaultEditTab(node):
        return "view"
        
    def processMediaFile(node, dest):
        for file in node.getFiles():
            if file.getType()=="video":
                filename = file.retrieveFile()
                path, ext = splitfilename(filename)
                if os.sep=='/':
                    ret = os.system("cp %s %s" %(filename, dest))
                else:
                    cmd = "copy %s %s%s.%s" %(filename, dest, node.id, ext)
                    ret = os.system(cmd.replace('/','\\'))
        return 1
  
