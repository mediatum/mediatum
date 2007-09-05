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
import athana
import tree
import search.query
import config

from tree import getNode
from frontend import shoppingbag
from metadatatypes import *
from mod.pdf import printview

from objtypes.metadatatype import VIEW_DATA_ONLY,VIEW_HIDE_EMPTY
from frontend.content import getPaths
from acl import AccessData
from translation import t,lang

#
# execute fullsize method from node-type
#
def popup_fullsize(req):
    access = AccessData(req)
    try:
        node = getNode(req.params["id"])
    except tree.NoSuchNodeError:
        return 404
    if not access.hasAccess(node,"data"):
        req.write(t(req, "permission_denied"))
        return
    node.popup_fullsize(req)
#
# add file to shoppingbag
#
def put_into_shoppingbag(req):
    dir = req.params.get("id", None)
    
    files = req.params["files"].split(',')
    
    try:
        f = req.session["shoppingbag"]
    except:
        f = []

    f += files
    req.session["shoppingbag"] = f

    req.writeTAL("popups.html", {}, macro="shoppingbag_add")
    return athana.HTTP_OK


#
# open shoppingbag window
#
def show_shoppingbag(req):
    if req.params.get("shoppingbag","")=="clear":
        req.session["shoppingbag"] = []
      
    (width,height) = shoppingbag.calculate_dimensions(req)
    v = {"width":width, "height":height}
    f = []

    img = False
    doc = False
    files = req.session.get("shoppingbag",[])

    for file in files:
        node = tree.getNode(file)
        if node.getType().getTypeName()=="image":
            img = True
        if node.getType().getTypeName() in("document", "dissertation"):
            doc = True
        f.append(node)

    v["files"] = f
    v["image"] = img
    v["document"] = doc

    req.writeTAL("popups.html", v, macro="shoppingbag")
    return athana.HTTP_OK

#
# index popup for metadatafields of type 'indexlist'
#
def show_index(req):
    try:
        name = req.params['name']
        fieldname = req.params.get('fieldname', name)

        index = search.query.getGlobalIndex(name)
        index.sort(lambda x,y: cmp(x.lower(), y.lower()))

        req.writeTAL("popups.html", {"index":index, "fieldname":fieldname}, macro="index")
        return athana.HTTP_OK
    except:
        print "missing request parameter"
        return athana.HTTP_NOT_FOUND

#
# help window for metadata field
#
def show_help(req):
    if req.params.get("maskid","")!="":
        field = getNode(req.params.get("maskid",""))
    else:
        field = getNode(req.params.get("id",""))

    req.writeTAL("popups.html", {"field":field}, macro="show_help")


#
# show attachmentbrowser for given node
# parameter: req.id, req.path
#
def show_attachmentbrowser(req):
    id = req.params.get("id")
    node = getNode(id)
    access = AccessData(req)
    if not access.hasAccess(node,"data"):
        req.write(t(req, "permission_denied"))
        return
    if node.getType().getName().startswith("document") or node.getType().getName().startswith("dissertation"):
        node.getAttachmentBrowser(req)
        
    
def show_printview(req):
    """ create a pdf preview of given node (id in path e.g. /print/[id])"""  
    node = getNode(int(req.path[1:].split("/")[1]))
    style = int(req.params.get("style",2))
    
    # nodetype
    mtype = getMetaType(node.getTypeName()[node.getTypeName().find("/")+1:])
    
    for m in mtype.getMasks():
        if m.getMasktype()=="fullview":
            mask = m
        if m.getMasktype()=="printview":
            mask = m
            break

    files = node.getFiles()
    imagepath = None
    for file in files:
        if file.getType().startswith("presentati"):
            imagepath = file.getPath()

    req.reply_headers['Content-Type'] = "application/pdf"
    req.write(printview.getPrintView(lang(req), imagepath, mask.getViewHTML([node], VIEW_DATA_ONLY+VIEW_HIDE_EMPTY), getPaths(node, AccessData(req)), style))
