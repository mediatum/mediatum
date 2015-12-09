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
import logging

from core.acl import AccessData
from web.frontend.content import getPaths
from core.translation import translate
from contenttypes import Collections
from core import Node
from core import db

logg = logging.getLogger(__name__)
q = db.query

def getData(req):
    access = AccessData(req)
    pid = req.params.get("parentId")
    style = req.params.get("style", "edittree")
    ret = []

    for c in q(Node).get(pid).children.sort_by_orderpos():
        if not access.hasReadAccess(c):
            continue
        try:
            if c.isContainer():
                cnum = len(c.container_children)
                inum = len(c.content_children)

                label = c.getLabel()
                title = label + " (" + unicode(c.id) + ")"

                cls = "folder"

                itemcls = ""
                if not c.has_write_access():
                    itemcls = "read"

                if c.type == "collection":  # or "collection" in c.type:
                    cls = "collection"
                if hasattr(c, 'treeiconclass'):
                    cls = c.treeiconclass()

                if c.name.startswith(translate('user_trash', request=req)):
                    cls = "trashicon"
                elif c.name.startswith(translate('user_upload', request=req)):
                    cls = "uploadicon"
                elif c.name.startswith(translate('user_import', request=req)):
                    cls = "importicon"
                elif c.name.startswith(translate('user_faulty', request=req)):
                    cls = "faultyicon"
                elif c.name.startswith(translate('user_directory', request=req)):
                    cls = "homeicon"

                if style == "edittree":  # standard tree for edit area
                    if inum > 0:
                        label += u" <small>({})</small>".format(inum)


                    ret.append(u'<li class="{}.gif" id="Node{}">'.format(cls, c.id))
                    ret.append(u'<a href="#" title="{}" id="{}" class="{}">{}</a>'.format(title, c.id, itemcls, label))

                    if cnum > 0:
                        ret.append(u'<ul><li parentId="{}" class="spinner.gif"><a href="#">&nbsp;</a></li></ul>'.format(c.id))
                    ret.append(u'</li>')

                elif style == "classification":  # style for classification
                    ret.append(u'<li class="{}.gif" id="Node{}">'.format(cls, c.id))
                    ret.append(u'<a href="#" title="{}" id="{}" class="{}">{}<input type="image" src="/img/ftree/uncheck.gif"/></a>'.format(
                                    title, c.id, itemcls, label))

                    if cnum > 0:
                        ret.append(u'<ul><li parentId="{}" class="spinner.gif"><a href="#">&nbsp;</a></li></ul>'.format(c.id))

                    ret.append(u'</li>')
        except:
            logg.exception("exception in getData")

    req.write(u"\n".join(ret))
    return


def getLabel(req):
    node = q(Node).get(req.params.get("getLabel"))

    inum = len(node.content_children)
    label = node.getLabel()
    if inum > 0:
        label += u" <small>({})</small>".format(inum)
    req.write(label)
    return


def getPathTo(req):
    # returns path(s) to selected node, 'x' separated, with selected nodes in ()
    # parameters: pathTo=selected Node
    access = AccessData(req)
    collectionsid = q(Collections).one().id
    id = req.params.get("pathTo", collectionsid).split(",")[0]
    node = q(Node).get(id)

    items = []
    checked = []

    for path in getPaths(node, access):
        if node.id not in path and node.isContainer():  # add node if container
            path.append(node)

        checked.append(unicode(path[-1].id))  # last item of path is checked

        if path[0].parents[0].id == collectionsid and collectionsid not in items:
            items.append(collectionsid)

        for item in path:
            if item.id not in items:
                items.append(item.id)

        items.append("x")  # set devider for next path
        if req.params.get("multiselect", "false") == "false":  # if not multiselect use only first path
            break

    if len(items) == 0 or collectionsid == q(Node).get(items[0]).parents[0].id:
        items = [collectionsid] + items

    items = u",".join([unicode(i) for i in items])

    for check in checked:  # set marked items
        items = items.replace(check, u'({})'.format(check))

    req.write(items)
    return
