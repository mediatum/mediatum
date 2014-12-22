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
import core.tree as tree

from core.tree import getNode
from web.edit.edit import printmethod
from schema.schema import getMetaType, getMetadataType
from lib.pdf import printview

from schema.schema import VIEW_DATA_ONLY, VIEW_HIDE_EMPTY
from web.frontend.content import getPaths
from core.acl import AccessData
from core.translation import t, lang
from utils.utils import u, getCollection
from core.styles import theme

#
# execute fullsize method from node-type
#


logg = logging.getLogger(__name__)


def popup_fullsize(req):
    #access = AccessData(req)
    try:
        node = getNode(req.params["id"])
    except tree.NoSuchNodeError:
        return 404
    # if not access.hasAccess(node,"data"):
    #    req.write(t(req, "permission_denied"))
    #    return
    node.popup_fullsize(req)
#
# execute thumbBig method from node-type
#


def popup_thumbbig(req):
    #access = AccessData(req)
    try:
        node = getNode(req.params["id"])
    except tree.NoSuchNodeError:
        return 404
    node.popup_thumbbig(req)


#
# help window for metadata field
#
def show_help(req):
    if req.params.get("maskid", "") != "":
        field = getNode(req.params.get("maskid", ""))
    else:
        field = getNode(req.params.get("id", ""))

    req.writeTAL(theme.getTemplate("popups.html"), {"field": field}, macro="show_help")

#
# show attachmentbrowser for given node
# parameter: req.id, req.path
#


def show_attachmentbrowser(req):
    id = req.params.get("id")
    node = getNode(id)
    access = AccessData(req)
    if not access.hasAccess(node, "data"):
        req.write(t(req, "permission_denied"))
        return
    # if node.getContentType().startswith("document") or node.getContentType().startswith("dissertation"):
    #    node.getAttachmentBrowser(req)
    from core.attachment import getAttachmentBrowser
    getAttachmentBrowser(node, req)


def getPrintChildren(req, node, ret):
    access = AccessData(req)

    for c in node.getChildren():
        if access.hasAccess(c, "read"):
            ret.append(c)

        getPrintChildren(req, c, ret)

    return ret


def show_printview(req):
    """ create a pdf preview of given node (id in path e.g. /print/[id]/[area])"""
    p = req.path[1:].split("/")
    try:
        nodeid = int(p[1])
    except ValueError:
        raise ValueError("Invalid Printview URL: " + req.path)

    if len(p) == 3:
        if p[2] == "edit":
            req.reply_headers['Content-Type'] = "application/pdf"
            editprint = printmethod(req)
            if editprint:
                req.write(editprint)
            else:
                req.write("")
            return

    # use objects from session
    if str(nodeid) == "0":
        children = []
        if "contentarea" in req.session:
            try:
                nodes = req.session["contentarea"].content.files
            except:
                c = req.session["contentarea"].content
                nodes = c.resultlist[c.active].files
            for n in nodes:
                c_mtype = getMetaType(n.getSchema())
                c_mask = c_mtype.getMask("printlist")
                if not c_mask:
                    c_mask = c_mtype.getMask("nodesmall")
                _c = c_mask.getViewHTML([n], VIEW_DATA_ONLY + VIEW_HIDE_EMPTY)
                if len(_c) > 0:
                    children.append(_c)

        req.reply_headers['Content-Type'] = "application/pdf"
        req.write(printview.getPrintView(lang(req), None, [["", "", t(lang(req), "")]], [], 3, children))

    else:
        node = getNode(nodeid)
        if node.get("system.print") == "0":
            return 404
        access = AccessData(req)
        if not access.hasAccess(node, "read"):
            req.write(t(req, "permission_denied"))
            return

        style = int(req.params.get("style", 2))

        # nodetype
        mtype = getMetaType(node.getSchema())

        mask = None
        metadata = None
        if mtype:
            for m in mtype.getMasks():
                if m.getMasktype() == "fullview":
                    mask = m
                if m.getMasktype() == "printview":
                    mask = m
                    break

            if not mask:
                mask = mtype.getMask("nodebig")

            if mask:
                metadata = mask.getViewHTML([node], VIEW_DATA_ONLY + VIEW_HIDE_EMPTY)

        if not metadata:
            metadata = [['nodename', node.getName(), 'Name', 'text']]

        files = node.getFiles()
        imagepath = None
        for file in files:
            if file.getType().startswith("presentati"):
                imagepath = file.retrieveFile()

        # children
        children = []
        if node.isContainer():
            ret = []
            getPrintChildren(req, node, ret)

            for c in ret:
                if not c.isContainer():
                    # items
                    c_mtype = getMetaType(c.getSchema())
                    c_mask = c_mtype.getMask("printlist")
                    if not c_mask:
                        c_mask = c_mtype.getMask("nodesmall")
                    _c = c_mask.getViewHTML([c], VIEW_DATA_ONLY)
                    if len(_c) > 0:
                        children.append(_c)
                else:
                    # header
                    items = getPaths(c, AccessData(req))
                    p = []
                    for item in items[0]:
                        p.append(u(item.getName()))
                    p.append(u(c.getName()))
                    children.append([(c.id, " > ".join(p[1:]), u(c.getName()), "header")])

            if len(children) > 1:
                col = []
                order = []
                try:
                    sort = getCollection(node).get("sortfield")
                except:
                    logg.exception("exception in show_printview, getting sortfield failed, setting sort = \"\"")
                    sort = ""

                for i in range(0, 2):
                    col.append((0, ""))
                    order.append(1)
                    if req.params.get("sortfield" + str(i)) != "":
                        sort = req.params.get("sortfield" + str(i), sort)

                    if sort != "":
                        if sort.startswith("-"):
                            sort = sort[1:]
                            order[i] = -1
                        _i = 0
                        for c in children[0]:
                            if c[0] == sort:
                                col[i] = (_i, sort)
                            _i += 1
                    if col[i][1] == "":
                        col[i] = (0, children[0][0][0])

                # sort method for items
                def myCmp(x, y, col, order):
                    cx = ""
                    cy = ""
                    for item in x:
                        if item[0] == col[0][1]:
                            cx = item[1]
                            break
                    for item in y:
                        if item[0] == col[0][1]:
                            cy = item[1]
                            break
                    if cx.lower() > cy.lower():
                        return 1 * order[0]
                    return -1 * order[0]

                sorted_children = []
                tmp = []
                for item in children:
                    if item[0][3] == "header":
                        if len(tmp) > 0:
                            tmp.sort(lambda x, y: myCmp(x, y, col, order))
                            sorted_children.extend(tmp)
                        tmp = []
                        sorted_children.append(item)
                    else:
                        tmp.append(item)
                tmp.sort(lambda x, y: myCmp(x, y, col, order))
                sorted_children.extend(tmp)
                children = sorted_children

        req.reply_headers['Content-Type'] = "application/pdf"
        req.write(printview.getPrintView(lang(req), imagepath, metadata, getPaths(
            node, AccessData(req)), style, children, getCollection(node)))

# use popup method of  metadatatype


def popup_metatype(req):
    mtype = getMetadataType(req.path.split("/")[-1])
    if mtype and hasattr(mtype, "getPopup"):
        mtype.getPopup(req)
    else:
        logg.error("error, no popup method found")
