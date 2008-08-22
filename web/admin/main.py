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
import os
import core.athana as athana
import core.config as config
import random
import core.users as users

from version import mediatum_version
from utils.utils import join_paths, Menu
from web.admin.adminutils import findmodule, show_content, adminNavigation, getMenuItemID

""" opens administration window with content """
def show_node(req):
    p = req.path[1:].split("/")
    style = req.params.get("style","")
    user = users.getUserFromRequest(req)

    v = {}
    v["user"] = user
    v["guestuser"] = config.get("user.guestuser")
    v["version"] = mediatum_version
    v["content"] = show_content(req, p[0])
    v["navigation"] = adminNavigation()
    v["breadcrumbs"] = getMenuItemID(v["navigation"], req.path[1:])
    v["spc"] = list()
    
    spc = list()
    v["spc"].append(Menu("sub_header_frontend", "sub_header_inquest_title","#", "/"))
    v["spc"].append(Menu("sub_header_edit", "sub_header_edit_title", "", "/edit"))
    if user.isWorkflowEditor():
        v["spc"].append(Menu("sub_header_workflow", "sub_header_workflow_title", "", "../publish"))

    if len(p)>0:
        if style == "":
            req.writeTAL("web/admin/frame.html", v, macro="frame")
        else:
            req.write(v["content"])
    return athana.HTTP_OK

""" export definition: url contains /[type]/[id] """
def export(req):
    path = req.path[1:].split("/")
    try:
        module = findmodule(path[1])

        tempfile = join_paths(config.get("paths.tempdir"), str(random.random()))
        file = open(tempfile, "w")
        file.write(module.export(req, path[2]))
        file.close()

        req.sendFile(tempfile, "application/xml")
        if os.sep == '/': # Unix?
            os.unlink(tempfile) # unlinking files while still reading them only works on Unix/Linux
    except:
        print "module has no export method"

