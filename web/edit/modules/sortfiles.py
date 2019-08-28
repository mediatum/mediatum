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

from sqlalchemy import func
from core.translation import t as _t
from core.transition import current_user
from core import httpstatus
from core import Node
from core import db
from schema.schema import Metadatatype
import web.common.sort as _sort

q = db.query


def getContent(req, ids):
    user = current_user
    node = q(Node).get(ids[0])

    if "sortfiles" in user.hidden_edit_functions or not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if "globalsort" in req.params:
        node.set("sortfield", req.params["globalsort"])
    collection_sortfield = node.get("sortfield")
    db.session.commit()

    sortchoices = _sort.get_sort_choices(container=node, off="off", t_off=_t(req, "off"), t_desc=_t(req, "descending"))

    return req.getTAL("web/edit/modules/sortfiles.html", dict(
            node=node,
            collection_sortfield=collection_sortfield,
            sortchoices=tuple(sortchoices),
            name=node.name,
        ), macro="edit_sortfiles")
