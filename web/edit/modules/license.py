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
from core.transition import httpstatus

def getContent(req, ids):
    if req.params.get("style","")=="popup":
        req.write(objlist(req))
        return ""
    
    user = users.getUserFromRequest(req)
    if "license" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
        
    node = tree.getNode(ids[0])
    return req.getTAL("web/edit/modules/license.html", {"node":node, "nodes": [node]}, macro="edit_license_info")

def objlist(req):
    node = tree.getNode(req.params["id"])
    access = AccessData(req)
    
    if node.id==tree.getRoot().id or not access.hasWriteAccess(node):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    return req.getTAL("web/edit/modules/license.html", {"node":node}, macro="edit_license")
