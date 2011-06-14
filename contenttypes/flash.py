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

from core.tree import Node,FileNode
from core.translation import lang, t
from core.acl import AccessData
import default 

from schema.schema import loadTypesFromDB, VIEW_HIDE_EMPTY,VIEW_DATA_ONLY

""" flash class """
class Flash(default.Default):
    def getTypeAlias(node):
        return "flash"

    def getCategoryName(node):
        return "video"

    def _prepareData(node, req, words=""):
        mask = node.getFullView(lang(req))
        obj = {}
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask) # hide empty elements
        else:
            obj['metadata'] = []  
        obj['node'] = node  
        obj['path'] = req.params.get("path","")
        return obj

    """ format big view with standard template """
    def show_node_big(node, req, template="contenttypes/flash.html", macro="showbig"):
        return req.getTAL(template, node._prepareData(req), macro)

    """ returns preview image """
    def show_node_image(node):
        return '<img src="/thumbs/'+node.id+'" class="thumbnail" border="0"/>'
     
    def isContainer(node):
        return 0

    def getSysFiles(node):
        return []

    def getLabel(node):
        return node.name

    """ list with technical attributes for type flash """
    def getTechnAttributes(node):
        return {"Standard":{"creationtime":"Erstelldatum",
                "creator":"Ersteller"}}


    """ popup window for actual nodetype """
    def popup_fullsize(node, req):
        access = AccessData(req)
        if not access.hasAccess(node, "data") or not access.hasAccess(node,"read"):
            req.write(t(req, "permission_denied"))
            return
            
        f = ""
        for filenode in node.getFiles():
            if filenode.getType() in ("original", "video"):
                f =  "/file/" + str(node.id) + "/" + filenode.getName()
                break
        req.writeTAL("contenttypes/flash.html", {"path":f}, macro="fullsize")
        
    def popup_thumbbig(node, req):
        node.popup_fullsize(req)
    
    def getEditMenuTabs(node):
        return "menulayout(view);menumetadata(metadata;files;lza);menuclasses(classes);menusecurity(acls)"
        
    def getDefaultEditTab(node):
        return "view"
        
