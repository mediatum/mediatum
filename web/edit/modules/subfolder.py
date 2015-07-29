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

import core.users as users
from core.acl import AccessData
from utils.utils import dec_entry_log
from schema.schema import getMetaType
from core.translation import lang
from core.transition import httpstatus
from core import Node
from core import db

q = db.query

logg = logging.getLogger(__name__)


@dec_entry_log
def getContent(req, ids):
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    language = lang(req)
    node = q(Node).get(ids[0])
    
    if "sort" in user.hidden_edit_functions or not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    logg.info("%s sorting subfolders of node %s (%s, %s): %s", user.login_name, node.id, node.name, node.type, req.params)

    if "order" in req.params:  # do reorder
        ids = req.params.get('order').split(',')
        children = []
        for n in ids:
            child = q(Node).get(n)
            child.orderpos = ids.index(n)
            children.append(child)
        db.session.commit()

        req.writeTAL('web/edit/modules/subfolder.html', {'nodelist': children, "language": language}, macro="ordered_list")
        return ""

    elif "sortdirection" in req.params:  # do automatic re-order
        sorted_children = node.container_children.order_by(Node.name).all()
        if req.params.get("sortdirection", "up") != "up":
            sorted_children.reverse()
        for position, child in enumerate(sorted_children, start=1):
            child.orderpos = position
        db.session.commit()
        req.writeTAL('web/edit/modules/subfolder.html', {'nodelist': sorted_children, "language": language}, macro="ordered_list")
        return ""

    nodelist = []
    attributes = []
    fields = {}
    i = 0
    for child in list(node.container_children.sort_by_orderpos()):
        i += 1  # count container children
        nodelist.append(child)
        if getMetaType(child.schema):
            for field in getMetaType(child.schema).getMetaFields():
                if not field in fields.keys():
                    fields[field] = 0
                fields[field] += 1

    for field in fields:
        if i == fields[field]:
            attributes.append(field)
    ctx = {
            "node": node,
            "nodelist": nodelist,
            "sortattributes": sorted(attributes, lambda x, y: cmp(x.getLabel().lower(), y.getLabel().lower())),
            "language": language,
           }
    return req.getTAL("web/edit/modules/subfolder.html", ctx, macro="edit_subfolder")
