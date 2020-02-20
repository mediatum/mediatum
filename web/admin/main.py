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
import codecs

import core
import mediatumtal.tal as _tal
import core.request_handler as _core_request_handler
from core import config
from core.users import get_guest_user
from core import httpstatus
from utils.utils import join_paths, Menu
from web.admin.adminutils import findmodule, show_content, adminNavigation, getMenuItemID
from core.users import user_from_session as _user_from_session


logg = logging.getLogger(__name__)


def show_node(req):
    """ opens administration window with content """

    p = req.path[1:].split("/")
    style = req.params.get("style", u"")
    user = _user_from_session()

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
            req.response.set_data(_tal.processTAL(v, file="web/admin/frame.html", macro="frame", request=req))
        else:
            req.response.set_data(v["content"])


def export(req):
    user = _user_from_session()
    """ export definition: url contains /[type]/[id] """

    if not user.is_admin:
        return httpstatus.HTTP_FORBIDDEN

    path = req.path[1:].split("/")
    module = findmodule(path[1])
    try:
        xml_result = module.export(req, path[2])
    except AttributeError as err:
        req.response.status_code = httpstatus.HTTP_NOT_FOUND
        _core_request_handler.error(req, httpstatus.HTTP_NOT_FOUND, str(err))

    req.response.status_code = httpstatus.HTTP_OK
    req.response.mimetype = "application/xml"
    req.response.set_data(xml_result)
