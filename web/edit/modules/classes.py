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

import core.users as users
from core.acl import AccessData
from core.translation import lang, t
from core.transition import httpstatus
from core import Node
from core.systemtypes import Root
from contenttypes import Collections, Home
from core import db

q = db.query
def getInformation():
    return {"version": "1.1", "system": 0}


def getContent(req, ids):
    ret = ""
    user = users.getUserFromRequest(req)
    access = AccessData(req)
    nodes = []
    for id in ids:
        if not access.hasWriteAccess(q(Node).get(id)):
            req.setStatus(httpstatus.HTTP_FORBIDDEN)
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")
        nodes += [q(Node).get(id)]

    if "classes" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    v = {}
    v["basedirs"] = [q(Home).one(), q(Collections).one()]
    id = req.params.get("id", q(Root).one().id)
    v["script"] = "var currentitem = '%s';\nvar currentfolder = '%s'" % (id, id)
    v["idstr"] = ",".join(ids)
    v["nodes"] = nodes
    v["t"] = t
    v["language"] = lang(req)
    return req.getTAL("web/edit/modules/classes.html", v, macro="classtree")
