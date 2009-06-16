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
import core.tree as tree
from utils.utils import formatTechAttrs,getMimeType
from utils.date import format_date
from utils.fileutils import importFile
import os
import core.users as users
import core.config as config
import logging
import core.acl as acl

def edit_files(req, ids):
    user = users.getUserFromRequest(req)
    node = tree.getNode(ids[0])
    update_error = False
    access = acl.AccessData(req)
    if not access.hasWriteAccess(node) or "files" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    mime = ""
    if req.params.get("postprocess","")!="":
        if hasattr(node,"event_files_changed"):
            try:
                node.event_files_changed()
            except "PostprocessingError":
                update_error = True

    if req.params.get("addfile","")!="":
        only_add = req.params.get("change_file", "no") == "no"

        user = users.getUserFromRequest(req)
        file = req.params.get("updatefile")

        for nfile in node.getFiles():
            if nfile.getType()=="original" or nfile.getType()=="doc":
                mime = nfile.getMimeType()

        if not file or file.filename=="":
            if not only_add:
                for nfile in node.getFiles():
                    node.removeFile(nfile)
        else:
            r = file.filename.lower()
            mimetype = "application/x-download"
            type = "file"
            
            mimetype, type = getMimeType(r)

            if mime!=mimetype and mime!="" and not only_add:
                req.writeTAL("web/edit/edit_files.html",{},macro="filetype_error")
            else:
                if not only_add:
                    for nfile in node.getFiles():
                        node.removeFile(nfile)

                logging.getLogger('usertracing').info(user.name + " upload "+file.filename+" ("+file.tempname+")")
                
                # set filename=nodename
                if not only_add or len(node.getFiles())==0:
                    node.setName(file.filename)
                    
                file = importFile(file.filename,file.tempname)
                if only_add and mime:
                    file.type = "extra"
                
                node.addFile(file)
                if hasattr(node,"event_files_changed"):
                    try:
                        node.event_files_changed()
                    except "PostprocessingError":
                        update_error = True

    req.writeTAL("web/edit/edit_files.html", {"id":req.params.get("id","0"), "tab":req.params.get("tab", ""), "node":node, "update_error":update_error}, macro="edit_files_file")


