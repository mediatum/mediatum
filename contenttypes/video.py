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

#from utils import *
#from date import *
from core.tree import Node,FileNode
from lib.flv.parse import getFLVSize
from contenttypes.image import makeThumbNail,makePresentationFormat
import default

""" video class """
class Video(default.Default):

    def _prepareData(node, req, words=""):
        access = acl.AccessData(req)
        mask = node.getMask("nodebig")
        obj = {}
        obj['metadata'] = mask.getViewHTML([node], 2) # hide empty elements
        obj['node'] = node  
        obj['path'] = req.params.get("path","")
        obj['canseeoriginal'] = access.hasAccess(node,"data")
        return obj

    """ format big view with standard template """
    def show_node_big(node, req):
        return req.getTAL("contenttypes/video.html", node._prepareData(req), macro="showbig")

    """ returns preview image """
    def show_node_image(node):
        return '<img src="/thumbs/'+node.id+'" class="thumbnail" border="0"/>'
    
    def event_files_changed(node):
        for f in node.getFiles():
            if f.type == "original" or f.type == "video":
                if f.mimetype == "video/x-flv":
                    width,height = getFLVSize(f.getPath())
                    node.set("vid-width", width)
                    node.set("vid-height", height)

                    tempname = os.path.join(config.get("paths.tempdir"),"tmp.gif")
                    try:
                        os.unlink(tempname);
                    except:
                        pass

                    try:
                        cmd = "ffmpeg -vframes 1 -i "+f.getPath()+" -pix_fmt rgb24 "+tempname
                        print cmd
                        ret = os.system(cmd)
                        if ret & 0xff00:
                            return
                    except:
                        return
                    path,ext = splitfilename(f.getPath())
                    thumbname = path+".thumb"
                    thumbname2 = path+".thumb2"
                    makeThumbNail(tempname, thumbname)
                    makePresentationFormat(tempname, thumbname2)
                    node.addFile(FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                    node.addFile(FileNode(name=thumbname2, type="presentation", mimetype="image/jpeg"))
     
    def can_open(node):
        return 0

    def getSysFiles(node):
        return []

    def getLabel(node):
        return node.name

    """ list with technical attributes for type video """
    def getTechnAttributes(node):
        return {"Standard":{"creationtime":"Erstelldatum",
                "creator":"Ersteller"}}


    """ popup window for actual nodetype """
    def popup_fullsize(node, req):
        for filenode in node.getFiles():
            if filenode.getType()=="original" or filenode.getType()=="video":
                f =  "/file/" + str(node.id) + "/" + str(splitpath(filenode.getPath())[1])
                break
        f = """config={ 
                    autoPlay: true, 
                    loop: false, 
                    initialScale: 'scale',
                    playList: [{ url: '""" +f+"""' }],
                    showPlayListButtons: true
                    }"""
        req.writeTAL("contenttypes/video.html", {"playervalues":f, "node":node}, macro="fullsize_flv")
