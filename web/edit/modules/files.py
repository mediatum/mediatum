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

import hashlib
import random
import core.tree as tree
import os
import core.users as users
import core.config as config
import logging
import core.acl as acl
from utils.utils import getMimeType
from utils.fileutils import importFile, getImportDir, importFileIntoDir
from contenttypes.image import makeThumbNail, makePresentationFormat


def getContent(req, ids):
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
                            # remove all files in directory
                            if file.getMimeType()=="inode/directory":
                                for root, dirs, files in os.walk(file.retrieveFile()):
                                    for name in files:
                                        try:
                                            os.remove(root+"/"+name)
                                        except:
                                            pass
                                    os.removedirs(file.retrieveFile()+"/")
                            # remove single file
                            node.removeFile(file)
                            try:
                                os.remove(file.retrieveFile())
                            except:
                                pass
                            break
                    break
                elif key.startswith("delatt|"):
                    for file in node.getFiles():
                        if file.getMimeType()=="inode/directory":
                            try:
                                os.remove(file.retrieveFile()+"/"+key.split("|")[2][:-2])
                            except:
                                pass
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

                if req.params.get("change_file") in ["yes", "no"]:
                    file = importFile(uploadfile.filename, uploadfile.tempname) # add new file
                    node.addFile(file)
                    logging.getLogger('usertracing').info(user.name+" changed file of node "+node.id+" to "+uploadfile.filename+" ("+uploadfile.tempname+")")
                    
                attpath = ""
                for f in node.getFiles():
                    if f.getMimeType()=="inode/directory":
                        attpath = f.getName()
                        break

                if req.params.get("change_file")=="attdir": # add attachmentdir
                    dirname = req.params.get("inputname")

                    if attpath=="": # add attachment directory
                        attpath = req.params.get("inputname")
                        if not os.path.exists(getImportDir() + "/" + attpath):
                            os.mkdir(getImportDir() + "/" + attpath)
                            node.addFile(tree.FileNode(name=getImportDir() + "/" + attpath, mimetype="inode/directory", type="attachment"))

                        file = importFileIntoDir(getImportDir() + "/" + attpath, uploadfile.tempname) # add new file
                    pass
                
                
                if req.params.get("change_file")=="attfile": # add file as attachment
                    if attpath=="":
                        # no attachment directory existing
                        file = importFile(uploadfile.filename, uploadfile.tempname) # add new file
                        file.mimetype = "inode/file"
                        file.type = "attachment"
                        node.addFile(file)
                    else:
                        # import attachment file into existing attachment directory
                        file = importFileIntoDir(getImportDir() + "/" + attpath, uploadfile.tempname) # add new file
                    pass

            
        elif op=="addthumb": # create new thumbanil from uploaded file
            uploadfile = req.params.get("updatefile")

            if uploadfile:
                thumbname = os.path.join(getImportDir(), hashlib.md5(str(random.random())).hexdigest()[0:8])+".thumb"

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
            
    v = {}
    v["id"] = req.params.get("id","0")
    v["tab"] = req.params.get("tab", "")
    v["node"] = node
    v["update_error"] = update_error
    v["user"] = user
    
    v["files"] = filter(lambda x: x.type!='statistic', node.getFiles())
    v["statfiles"] = filter(lambda x: x.type=='statistic', node.getFiles())
    v["attfiles"] = filter(lambda x: x.type=='attachment', node.getFiles())
    v["att"] = []
    for f in v["attfiles"]: # collect all files in attachment directory
        if f.getMimeType()=="inode/directory":
            for root, dirs, files in os.walk(f.retrieveFile()):
                for name in files:
                    af = tree.FileNode(root+"/"+name, "attachmentfile", getMimeType(name)[0])
                    v["att"].append(af)

    return req.getTAL("web/edit/modules/files.html", v, macro="edit_files_file")    
    
