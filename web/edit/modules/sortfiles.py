# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

from sqlalchemy import func
from core.translation import t as _t
from utils.utils import getCollection
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core import db
from schema.schema import Metadatatype
import web.common.sort as _sort

q = db.query


def getContent(req, ids):
    user = _user_from_session()
    node = q(Node).get(ids[0])

    if "sortfiles" in user.hidden_edit_functions or not node.has_write_access():
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if "globalsort" in req.params:
        node.set("sortfield", req.params["globalsort"])
    collection_sortfield = node.get("sortfield")
    db.session.commit()

    sortchoices = _sort.get_sort_choices(container=node, off="off", t_off=_t(req, "off"), t_desc=_t(req, "descending"))
    return _tal.processTAL({"node": node,
                            "collection_sortfield": collection_sortfield,
                            "sortchoices": tuple(sortchoices),
                            "name": node.name}, file="web/edit/modules/sortfiles.html", macro="edit_sortfiles", request=req)
