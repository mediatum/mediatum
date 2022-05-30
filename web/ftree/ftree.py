# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import mediatumtal.tal as _tal
import core.httpstatus as _httpstatus
from core import db
from core.users import user_from_session as _user_from_session
from contenttypes import Container, Content
from .ftreedata import getData, getPathTo, getLabel


q = db.query
logg = logging.getLogger(__name__)


def ftree(req):

    user = _user_from_session()
    if not user.is_editor:
        logg.warning("ftree permission denied for user: %s", user.id)
        req.response.status_code = 403
        return 403

    if "parentId" in req.params:
        return getData(req)

    if "pathTo" in req.params:
        return getPathTo(req)

    if "getLabel" in req.params:
        return getLabel(req)

    if "changeCheck" in req.params:
        for id in req.params.get("currentitem").split(","):
            node = q(Content).get(id)
            parent = q(Container).get(req.params.get("changeCheck"))
            if not(node and parent and node.has_write_access() and parent.has_write_access()):
                logg.warning("illegal ftree request: %s", req.params)
                req.response.status_code = 403
                return 403

            if node in parent.content_children:
                if len(node.parents) > 1:
                    parent.content_children.remove(node)
                    logg.info("ftree change ")
                    req.response.status_code = _httpstatus.HTTP_OK
                    db.session.commit()
                else:
                    req.response.status_code = _httpstatus.HTTP_OK
                    req.response.set_data(_tal.processTAL({}, string='<tal:block i18n:translate="edit_classes_noparent"/>', macro=None, request=req))
            else:
                req.response.status_code = _httpstatus.HTTP_OK
                parent.content_children.append(node)
                db.session.commit()
