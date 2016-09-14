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


from core.transition import httpstatus, current_user
from core import Node
from core import db
from core.systemtypes import Root
from utils.utils import get_hash

q = db.query

def getContent(req, ids):
    if req.params.get("style","")=="popup":
        req.write(objlist(req))
        return ""

    user = current_user
    if "license" in user.hidden_edit_functions:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    node = q(Node).get(ids[0])
    return req.getTAL("web/edit/modules/license.html", {"node":node, "nodes": [node]}, macro="edit_license_info")

def objlist(req):
    node = q(Node).get(req.params["id"])

    if node.id==q(Root).one().id or not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    return req.getTAL("web/edit/modules/license.html", {"children": node.all_children,
                                                        'hash_function': get_hash},
                      macro="edit_license")