# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging

import mediatumtal.tal as _tal
from schema.schema import getMetaType
from core.translation import lang
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core import db

q = db.query

logg = logging.getLogger(__name__)


def getContent(req, ids):
    user = _user_from_session()
    language = lang(req)
    node = q(Node).get(ids[0])
    
    if "sort" in user.hidden_edit_functions or not node.has_write_access():
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    logg.info("%s sorting subfolders of node %s (%s, %s): %s", user.login_name, node.id, node.name, node.type, req.params)

    if "order" in req.params:  # do reorder
        ids = req.params.get('order').split(',')
        children = []
        for n in ids:
            child = q(Node).get(n)
            child.orderpos = ids.index(n)
            children.append(child)
        db.session.commit()

        req.response.set_data(_tal.processTAL({'nodelist': children, "language": language, "csrf": req.csrf_token.current_token}, file='web/edit/modules/subfolder.html', macro="ordered_list", request=req))
        return ""

    elif "sortdirection" in req.params:  # do automatic re-order
        sorted_children = node.container_children.order_by(Node.name).all()
        if req.params.get("sortdirection", "up") != "up":
            sorted_children.reverse()
        for position, child in enumerate(sorted_children, start=1):
            child.orderpos = position
        db.session.commit()
        req.response.set_data(_tal.processTAL({'nodelist': sorted_children, "language": language, "csrf": req.csrf_token.current_token}, file='web/edit/modules/subfolder.html', macro="ordered_list", request=req))
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
            "csrf": req.csrf_token.current_token
           }
    return _tal.processTAL(ctx, file="web/edit/modules/subfolder.html", macro="edit_subfolder", request=req)
