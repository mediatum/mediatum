"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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

import core.tree as tree
from core.acl import AccessData
from web.frontend.content import getPaths
from core.translation import translate


def getData(req):
    access = AccessData(req)
    pid = req.params.get("parentId")
    style = req.params.get("style", "edittree")
    ret = []

    for c in tree.getNode(pid).getChildren().sort_by_orderpos():
        if not access.hasReadAccess(c):
            continue
        try:
            if c.isContainer():
                cnum = len(c.getContainerChildren())
                inum = len(c.getContentChildren())

                label = c.getLabel()
                title = c.getLabel() + " (" + str(c.id) + ")"

                cls = "folder"

                itemcls = ""
                if not access.hasWriteAccess(c):
                    itemcls = "read"

                if c.type == "collection":  # or "collection" in c.type:
                    cls = "collection"
                if hasattr(c, 'treeiconclass'):
                    cls = c.treeiconclass()

                if c.getName().startswith(translate('user_trash', request=req)):
                    cls = "trashicon"
                elif c.getName().startswith(translate('user_upload', request=req)):
                    cls = "uploadicon"
                elif c.getName().startswith(translate('user_import', request=req)):
                    cls = "importicon"
                elif c.getName().startswith(translate('user_faulty', request=req)):
                    cls = "faultyicon"
                elif c.getName().startswith(translate('user_directory', request=req)):
                    cls = "homeicon"

                if style == "edittree":  # standard tree for edit area
                    if inum > 0:
                        label += " <small>(" + str(inum) + ")</small>"

                    ret.append('<li class="' + cls + '.gif" id="Node' + c.id + '">')
                    ret.append('<a href="#" title="' + title + '" id="' + c.id + '" class="' + itemcls + '">' + label + '</a>')

                    if cnum > 0:
                        ret.append('<ul><li parentId="' + c.id + '" class="spinner.gif"><a href="#">&nbsp;</a></li></ul>')
                    ret.append('</li>')

                elif style == "classification":  # style for classification
                    ret.append('<li class="' + cls + '.gif" id="Node' + c.id + '">')
                    ret.append('<a href="#" title="' + title + '" id="' + c.id + '" class="' + itemcls +
                               '">' + label + ' <input type="image" src="/img/ftree/uncheck.gif"/></a>')

                    if cnum > 0:
                        ret.append('<ul><li parentId="' + c.id + '" class="spinner.gif"><a href="#">&nbsp;</a></li></ul>')

                    ret.append('</li>')
        except:
            pass

    req.write("\n".join(ret))
    return


def getLabel(req):
    node = tree.getNode(req.params.get("getLabel"))
    style = req.params.get("style", "edittree")

    inum = len(node.getContentChildren())
    label = node.getLabel()
    if inum > 0:
        label += " <small>(" + str(inum) + ")</small>"
    req.write(label)
    return


def getPathTo(req):
    # returns path(s) to selected node, 'x' separated, with selected nodes in ()
    # parameters: pathTo=selected Node
    access = AccessData(req)
    collectionsid = tree.getRoot('collections').id
    id = req.params.get("pathTo", collectionsid).split(",")[0]
    node = tree.getNode(id)

    items = []
    checked = []

    for path in getPaths(node, access):
        if node.id not in path and node.isContainer():  # add node if container
            path.append(node)

        checked.append(path[-1].id)  # last item of path is checked

        if path[0].getParents()[0].id == collectionsid and collectionsid not in items:
            items.append(collectionsid)

        for item in path:
            if item.id not in items:
                items.append(item.id)

        items.append("x")  # set devider for next path
        if req.params.get("multiselect", "false") == "false":  # if not multiselect use only first path
            break

    if len(items) == 0 or collectionsid in tree.getNode(items[0]).getParents()[0].id:
        items = [collectionsid] + items

    items = (",").join(items)

    for check in checked:  # set marked items
        items = items.replace(check, "(%s)" % (check))

    req.write(items)
    return
