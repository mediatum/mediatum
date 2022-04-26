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
from __future__ import print_function

import mediatumtal.tal as _tal

from core.translation import lang, t
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core.systemtypes import Root
from contenttypes import Collections, Home
from core import db

q = db.query
def getInformation():
    return {"version": "1.1", "system": 0}


def getContent(req, ids):
    user = _user_from_session()
    nodes = []
    for nid in ids:
        node = q(Node).get(nid)
        if not node.has_write_access():
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)
        nodes.append(node)

    if "classes" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    v = {}
    v["basedirs"] = [q(Home).one(), q(Collections).one()]
    nid = req.params.get("id", q(Root).one().id)
    v["script"] = "var currentitem = '%s';\nvar currentfolder = '%s'" % (nid, nid)
    v["idstr"] = ",".join(ids)
    v["nodes"] = nodes
    v["t"] = t
    v["language"] = lang(req)
    return _tal.processTAL(v, file="web/edit/modules/classes.html", macro="classtree", request=req)
