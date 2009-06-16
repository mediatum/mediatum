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

import core.tree as tree
import os
import logging
import core.acl as acl
import core.users as users

from utils.utils import getMimeType, splitpath
from utils.fileutils import importFile

def edit_logo(req, ids):

    user = users.getUserFromRequest(req)
    if "logo" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    node = tree.getNode(ids[0])
    access = acl.AccessData(req)
    
    if not access.hasWriteAccess(node):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return
    
    # save logo
    if "logo_save" in req.params.keys():
        # save url
        if req.params.get("logo_link","")=="":
            node.removeAttribute("url")
        else:
            node.set('url', req.params.get("logo_link"))
 
        # save filename
        if req.params.get("logo")=="nologo":
            # remove logo from current node
            node.removeAttribute("system.logo")

        elif req.params.get("logo")!="":
            node.set("system.logo", req.params.get("logo"))

    # add logo file
    elif "addfile" in req.params.keys():
        file = req.params.get("updatefile")
        if file:      
            mimetype = "application/x-download"
            type = "file"
            mimetype, type = getMimeType(file.filename.lower())

            if mimetype not in ("image/jpeg", "image/gif", "image/png"):
                # wrong file type (jpeg, jpg, gif, png)
                req.writeTAL("web/edit/edit_logo.html", {}, macro="filetype_error")
                return
            else:
                file = importFile(file.filename,file.tempname)
                node.addFile(file)
    logofiles = []
    for f in node.getFiles():
        if f.getType()=="image":
            logofiles.append(splitpath(f.retrieveFile()))

    req.writeTAL("web/edit/edit_logo.html", {"id":req.params.get("id","0"), "tab":req.params.get("tab", ""), "node":node, "logofiles":logofiles, "logo":node.getLogoPath()}, macro="edit_logo")
