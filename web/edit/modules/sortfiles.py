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
from __future__ import division

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
