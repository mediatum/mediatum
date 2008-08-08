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

from utils.utils import splitpath, Menu
from core.tree import Node,FileNode
import default 

""" flash class """
class Flash(default.Default):

    def _prepareData(node, req, words=""):
        mask = node.getMask("nodebig")
        obj = {}
        obj['metadata'] = mask.getViewHTML([node], 2) # hide empty elements
        obj['node'] = node  
        obj['path'] = req.params.get("path","")
        return obj

    """ format big view with standard template """
    def show_node_big(node, req):
        return req.getTAL("contenttypes/flash.html", node._prepareData(req), macro="showbig")

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
        f = ""
        for filenode in node.getFiles():
            if filenode.getType() in ("original", "video"):
                f =  "/file/" + str(node.id) + "/" + filenode.getName()
                break
        req.writeTAL("contenttypes/flash.html", {"path":f}, macro="fullsize")
    
    def getEditMenuTabs(node):
        menu = list()
        try:
            submenu = Menu("tab_layout", "description","#", "../") #new
            submenu.addItem("tab_view","tab_view")
            menu.append(submenu)
            
            submenu = Menu("tab_metadata", "description","#", "../") # new
            submenu.addItem("tab_metadata","tab_metadata")
            submenu.addItem("tab_files_obj","tab_files")
            submenu.addItem("tab_lza", "tab_lza")
            menu.append(submenu)
            
            submenu = Menu("tab_classes_header", "description","#", "../") # new
            submenu.addItem("tab_classes","tab_classes")
            menu.append(submenu)

            submenu = Menu("tab_security", "description","#", "../") # new
            submenu.addItem("tab_acls","tab_acls")
            menu.append(submenu)

        except TypeError:
            pass
        return menu
        
    def getDefaultEditTab(node):
        return "tab_view"
        
