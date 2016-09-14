"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>

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
import logging

from utils.utils import getMimeType, splitpath, dec_entry_log
from utils.fileutils import importFile

from core.translation import lang
from core.translation import t as translation_t
from core.transition import httpstatus, current_user
from core import Node
from core import db

q = db.query

logg = logging.getLogger(__name__)


# to do: limit number of logos

@dec_entry_log
def getContent(req, ids):
    user = current_user
    node = q(Node).get(ids[0])

    if "logo" in current_user.hidden_edit_functions or not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    # delete logo file
    if "action" in req.params and req.params.get('action') == "delete":
        file = req.params.get('file').split("/")[-1]
        for f in node.files:
            if f.abspath.endswith(file):
                node.files.remove(f)
                db.session.commit()
                req.write('ok')
                return None
        req.write('not found')
        return None

    # add logo file
    if "addfile" in req.params.keys():
        file = req.params.get("updatefile")
        if file:
            mimetype = "application/x-download"
            type = "file"
            mimetype, type = getMimeType(file.filename.lower())

            if mimetype not in ("image/jpeg", "image/gif", "image/png"):
                # wrong file type (jpeg, jpg, gif, png)
                req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
                return req.getTAL("web/edit/modules/logo.html", {}, macro="filetype_error")
            else:
                file = importFile(file.filename, file.tempname)
                node.files.append(file)
                db.session.commit()

    # save logo
    if "logo_save" in req.params.keys():
        # save url
        if req.params.get("logo_link", "") == "":
            if 'url' in node.attrs:
                del node.attrs['url']
        else:
            node.set('url', req.params.get("logo_link"))

        # save filename
        if req.params.get('logo') == "/img/empty.gif":
            # remove logo from current node
            node.set("system.logo", "")
            logg.info("%s cleared logo for node %s (%s, %s)", user.login_name, node.id, node.name, node.type)
        else:
            node.set("system.logo", req.params.get("logo").split("/")[-1])
            logg.info("%s set logo for node %s (%s, %s) to %s", user.login_name, node.id, node.name, node.type, node.get("system.logo"))

        db.session.commit()

    logofiles = []
    for f in node.files:
        if f.filetype == "image":
            logofiles.append(splitpath(f.abspath))
    
    v = {
        "id": req.params.get("id", "0"),
        "tab": req.params.get("tab", ""),
        "node": node,
        "logofiles": logofiles,
        "logo": node.getLogoPath(),
        "language": lang(req),
        "t": translation_t
    }
         
    return req.getTAL("web/edit/modules/logo.html", v, macro="edit_logo")
