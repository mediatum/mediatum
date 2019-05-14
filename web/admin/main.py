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
import random
import codecs

import core
from core import config
from core.users import get_guest_user
from core import httpstatus
from utils.utils import join_paths, Menu
from web.admin.adminutils import findmodule, show_content, adminNavigation, getMenuItemID
from core.transition import current_user
from core.request_handler import sendFile as _sendFile


logg = logging.getLogger(__name__)


def show_node(req):
    """ opens administration window with content """

    p = req.path[1:].split("/")
    style = req.params.get("style", u"")
    user = current_user

    v = {}
    v["user"] = user
    v["guestuser"] = get_guest_user().login_name
    v["version"] = core.__version__
    v["content"] = show_content(req, p[0])
    v["navigation"] = adminNavigation()
    v["breadcrumbs"] = getMenuItemID(v["navigation"], req.path[1:])

    spc = [
        Menu("sub_header_frontend", u"/"),
        Menu("sub_header_edit", u"/edit"),
        Menu("sub_header_logout", u"/logout")
    ]

    if user.is_workflow_editor:
        spc.append(Menu("sub_header_workflow", u"../publish/"))

    v["spc"] = spc

    if len(p) > 0:
        if style == "":
            req.writeTAL("web/admin/frame.html", v, macro="frame")
        else:
            req.write(v["content"])


def export(req):
    """ export definition: url contains /[type]/[id] """

    if not current_user.is_admin:
        return httpstatus.HTTP_FORBIDDEN

    path = req.path[1:].split("/")
    try:
        module = findmodule(path[1])

        tempfile = join_paths(config.get("paths.tempdir"), str(random.random()))
        with codecs.open(tempfile, "w", encoding='utf8') as f:
            try:
                f.write(module.export(req, path[2]))
            except UnicodeDecodeError:
                f.write(module.export(req, path[2]).decode('utf-8'))

        _sendFile(req, tempfile, u"application/xml", nginx_x_accel_redirect_enabled=False)
        if os.sep == '/':  # Unix?
            os.unlink(tempfile)  # unlinking files while still reading them only works on Unix/Linux
    except:
        logg.info("module has no export method")
