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
import logging
import os
from core.transition import httpstatus
import core.config as config
import random
import codecs
import core.users as users
import core.help as help

from version import mediatum_version
from utils.utils import join_paths, Menu
from web.admin.adminutils import findmodule, show_content, adminNavigation, getMenuItemID


logg = logging.getLogger(__name__)


def show_node(req):
    """ opens administration window with content """

    p = req.path[1:].split("/")
    style = req.params.get("style", u"")
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
    v["spc"].append(Menu("sub_header_frontend", u"/"))
    v["spc"].append(Menu("sub_header_edit", u"/edit"))
    if user.isWorkflowEditor():
        v["spc"].append(Menu("sub_header_workflow", u"../publish"))
    v["spc"].append(Menu("sub_header_logout", u"/logout"))
    v["hashelp"] = help.getHelpPath(['admin', 'modules', req.path.split('/')[1]])

    if len(p) > 0:
        if style == "":
            req.writeTAL("web/admin/frame.html", v, macro="frame")
        else:
            req.write(v["content"])


def export(req):
    """ export definition: url contains /[type]/[id] """

    user = users.getUserFromRequest(req)
    if not user.isAdmin():
        return httpstatus.HTTP_FORBIDDEN

    path = req.path[1:].split("/")
    try:
        module = findmodule(path[1])

        tempfile = join_paths(config.get("paths.tempdir"), ustr(random.random()))
        with codecs.open(tempfile, "w", encoding='utf8') as f:
            f.write(module.export(req, path[2]))

        req.sendFile(tempfile, u"application/xml")
        if os.sep == '/':  # Unix?
            os.unlink(tempfile)  # unlinking files while still reading them only works on Unix/Linux
    except:
        logg.info("module has no export method")
