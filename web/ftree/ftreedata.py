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

from core.translation import translate, lang
from core.transition import current_user
from contenttypes import Collections, Container
from core import Node
from core import db
from web.edit.edit import get_special_dir_type
from web.edit.edit_common import get_edit_label
from core.systemtypes import Root
from utils.pathutils import getPaths

logg = logging.getLogger(__name__)
q = db.query


def getData(req):
    pid = req.params.get("parentId")
    style = req.params.get("style", "edittree")
    ret = []

    for c in q(Node).get(pid).children.filter_read_access().order_by(Node.orderpos):
        try:
            if isinstance(c, Container):
                special_dir_type = get_special_dir_type(c)
                cnum = c.container_children.count()
                inum = c.content_children.count()

                label = get_edit_label(c, lang(req))
                title = label + " (" + unicode(c.id) + ")"

                cls = "folder"

                itemcls = ""
                if not c.has_write_access():
                    itemcls = "read"

                if c.type == "collection":  # or "collection" in c.type:
                    cls = "collection"
                if hasattr(c, 'treeiconclass'):
                    cls = c.treeiconclass()

                if special_dir_type == u'trash':
                    cls = "trashicon"
                elif special_dir_type == u'upload':
                    cls = "uploadicon"
                elif c == current_user.home_dir:
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
    collectionsid = q(Collections).one().id
    # if more than one node selected use the first to get the path to
    nid = req.args.get("pathTo", collectionsid).split(',')[0]
    if not nid:
        raise ValueError("node id must be numeric, got '{}'".format(req.args.get("pathTo")))
    node = q(Node).get(nid)

    items = []
    checked = []

    for path in getPaths(node):
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
