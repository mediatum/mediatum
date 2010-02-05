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

import md5
import random
import core.tree as tree
import os
import core.users as users
import core.config as config
import logging
import core.acl as acl
from utils.utils import getMimeType
from utils.fileutils import importFile, getImportDir
from contenttypes.image import makeThumbNail, makePresentationFormat


def getContent(req, ids):
    print req.params
    
    user = users.getUserFromRequest(req)
    node = tree.getNode(ids[0])
    update_error = False
    access = acl.AccessData(req)
    if not access.hasWriteAccess(node) or "files" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
        
        
    if "operation" in req.params:
        op = req.params.get("operation")
        if op=="delete":
            for key in req.params.keys(): # delete file
                if key.startswith("del|"):
                    filename = key[4:-2].split("|")
                    for file in node.getFiles():
                        if file.getName()==filename[1] and file.type==filename[0]:
                            node.removeFile(file)
                            break
                    break
                    
        elif op=="change":
            uploadfile = req.params.get("updatefile")

            if uploadfile:
                if req.params.get("change_file")=="yes": # remove old files
                    for f in node.getFiles():
                        if f.getType() in node.getSysFiles():
                            node.removeFile(f)
                            if os.path.exists(f.retrieveFile()): # delete file from disc
                                os.remove(f.retrieveFile())

                file = importFile(uploadfile.filename, uploadfile.tempname) # add new file
                node.addFile(file)
                logging.getLogger('usertracing').info(user.name+" changed file of node "+node.id+" to "+uploadfile.filename+" ("+uploadfile.tempname+")")
            
        elif op=="addthumb": # create new thumbanil from uploaded file
            uploadfile = req.params.get("updatefile")

            if uploadfile:
                thumbname = os.path.join(getImportDir(), md5.md5(str(random.random())).hexdigest()[0:8])+".thumb"

                file = importFile(thumbname, uploadfile.tempname) # add new file
                makeThumbNail(file.retrieveFile(), thumbname)
                makePresentationFormat(file.retrieveFile(), thumbname+"2")
                
                if os.path.exists(file.retrieveFile()): # remove uploaded original
                    os.remove(file.retrieveFile())
                
                for f in node.getFiles():
                    if f.type in ["thumb", "presentation", "presentati"]:
                        if os.path.exists(f.retrieveFile()):
                            os.remove(f.retrieveFile())
                        node.removeFile(f)
 
                node.addFile(tree.FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                node.addFile(tree.FileNode(name=thumbname+"2", type="presentation", mimetype="image/jpeg"))
                logging.getLogger('usertracing').info(user.name+" changed thumbnail of node "+node.id)
            
        elif op=="postprocess":
            if hasattr(node, "event_files_changed"):
                try:
                    node.event_files_changed()
                    logging.getLogger('usertracing').info(user.name+" postprocesses node "+node.id)
                except "PostprocessingError":
                    update_error = True
            
    return req.getTAL("web/edit/modules/files.html", {"id":req.params.get("id","0"), "tab":req.params.get("tab", ""), "node":node, "update_error":update_error}, macro="edit_files_file")    
    
