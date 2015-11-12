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
import logging
import core.acl as acl
from utils.utils import getMimeType, get_user_id, log_func_entry, dec_entry_log
from utils.fileutils import importFile, getImportDir, importFileIntoDir
from contenttypes.image import makeThumbNail, makePresentationFormat
from core.transition import httpstatus

log = logging.getLogger('editor')

from core.translation import lang, t
import core.db.mysqlconnector as mysqlconnector


def getContent(req, ids):
    ret = ""
    user = users.getUserFromRequest(req)
    node = tree.getNode(ids[0])
    update_error = False
    access = acl.AccessData(req)

    msg = "%s|web.edit.modules.files.getContend|req.fullpath=%r|req.path=%r|req.params=%r|ids=%r" % (get_user_id(req), req.fullpath, req.path, req.params, ids)
    log.debug(msg)

    if not access.hasWriteAccess(node) or "files" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if 'data' in req.params:
        if req.params.get('data') == 'children':  # get formated list of childnodes of selected directory
            req.writeTAL("web/edit/modules/files.html", {'children': node.getChildren()}, macro="edit_files_popup_children")

        if req.params.get('data') == 'additems':  # add selected node as children
            for childid in req.params.get('items').split(";"):
                if childid.strip() != "":
                    childnode = tree.getNode(childid.strip())
                    for p in childnode.getParents():
                        p.removeChild(childnode)
                    node.addChild(childnode)
            req.writeTAL("web/edit/modules/files.html", {'children': node.getChildren(), 'node': node}, macro="edit_files_children_list")

        if req.params.get('data') == 'removeitem':  # remove selected childnode node
            try:
                remnode = tree.getNode(req.params.get('remove'))
                if len(remnode.getParents()) == 1:
                    users.getUploadDir(user).addChild(remnode)
                node.removeChild(remnode)
            except: # node not found
                pass
            req.writeTAL("web/edit/modules/files.html", {'children': node.getChildren(), 'node': node}, macro="edit_files_children_list")

        if req.params.get('data') == 'reorder':
            i = 0
            for id in req.params.get('order').split(","):
                if id != "":
                    n = tree.getNode(id)
                    n.setOrderPos(i)
                    i += 1

        if req.params.get('data') == 'translate':
            req.writeTALstr('<tal:block i18n:translate="" tal:content="msgstr"/>', {'msgstr': req.params.get('msgstr')})
        return ""

    if req.params.get("style") == "popup":
        v = {"basedirs": [tree.getRoot('home'), tree.getRoot('collections')]}
        id = req.params.get("id", tree.getRoot().id)
        v["script"] = "var currentitem = '%s';\nvar currentfolder = '%s';\nvar node = %s;" %(id, req.params.get('parent'), id)
        v["idstr"] = ",".join(ids)
        v["node"] = node
        req.writeTAL("web/edit/modules/files.html", v, macro="edit_files_popup_selection")
        return ""

    if "operation" in req.params:
        op = req.params.get("operation")
        if op == "delete":
            for key in req.params.keys():  # delete file
                if key.startswith("del|"):
                    filename = key[4:-2].split("|")
                    for file in node.getFiles():
                        if file.getName() == filename[1] and file.type == filename[0]:
                            # remove all files in directory
                            if file.getMimeType() == "inode/directory":
                                for root, dirs, files in os.walk(file.retrieveFile()):
                                    for name in files:
                                        try:
                                            os.remove(root + "/" + name)
                                        except:
                                            pass
                                    os.removedirs(file.retrieveFile()+"/")
                            if len([f for f in node.getFiles() if f.getName()==filename[1] and f.type==filename[0]]) > 1:
                                # remove single file from database if there are duplicates
                                node.removeFile(file, single=True)
                            else:
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
                        if file.getMimeType() == "inode/directory":
                            try:
                                os.remove(file.retrieveFile() + "/" + key.split("|")[2][:-2])
                            except:
                                pass
                            break
                    break

        elif op=="change":
            uploadfile = req.params.get("updatefile")

            if uploadfile:
                create_version_error = False
                # Create new version when change file
                if (req.params.get('generate_new_version') and not hasattr(node, "metaFields")):
                    if (req.params.get('version_comment', '').strip()==''
                        or req.params.get('version_comment', '').strip()=='&nbsp;'):
                        create_version_error = True
                        req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
                        ret += req.getTAL("web/edit/modules/files.html", {}, macro="version_error")
                    else:
                        current = node
                        node = node.createNewVersion(user)

                        for attr, value in current.items():
                            if node.get(attr)!="": # do not overwrite attributes
                                pass
                            else:
                                node.set(attr, value)
                        req.setStatus(httpstatus.HTTP_MOVED_TEMPORARILY)
                        ret += req.getTAL("web/edit/modules/metadata.html", {'url':'?id='+node.id+'&tab=files', 'pid':None}, macro="redirect")

                if req.params.get("change_file")=="yes" and not create_version_error: # remove old files
                    if uploadfile.filename:
                        if getMimeType(uploadfile.filename)[0] == 'other':
                            return '<h2 style="width:100%; text-align:center ;color:red">file-format is not supported (upload canceled / use attachment)</h2>'
                    for f in node.getFiles():
                        if f.getType() in node.getSysFiles():
                            node.removeFile(f)
                    node.set("system.version.comment", '('+t(req, "edit_files_new_version_exchanging_comment")+')\n'+req.params.get('version_comment', ''))

                if req.params.get("change_file")=="no" and not create_version_error:
                    node.set("system.version.comment", '('+t(req, "edit_files_new_version_adding_comment")+')\n'+req.params.get('version_comment', ''))

                if req.params.get("change_file") in ["yes", "no"] and not create_version_error:
                    if uploadfile.filename:
                        if getMimeType(uploadfile.filename)[0] == 'other':
                            return '<h2 style="width:100%; text-align:center ;color:red">file-format is not supported (upload canceled / use attachment)</h2>'
                    file = importFile(uploadfile.filename, uploadfile.tempname) # add new file
                    node.addFile(file)
                    logging.getLogger('usertracing').info(user.name+" changed file of node "+node.id+" to "+uploadfile.filename+" ("+uploadfile.tempname+")")

                attpath = ""
                for f in node.getFiles():
                    if f.getMimeType()=="inode/directory":
                        attpath = f.getName()
                        break

                if req.params.get("change_file")=="attdir" and not create_version_error: # add attachmentdir
                    dirname = req.params.get("inputname")

                    if attpath=="": # add attachment directory
                        attpath = req.params.get("inputname")
                        if not os.path.exists(getImportDir() + "/" + attpath):
                            os.mkdir(getImportDir() + "/" + attpath)
                            node.addFile(tree.FileNode(name=getImportDir() + "/" + attpath, mimetype="inode/directory", type="attachment"))

                        file = importFileIntoDir(getImportDir() + "/" + attpath, uploadfile.tempname) # add new file
                    node.set("system.version.comment", '('+t(req, "edit_files_new_version_attachment_directory_comment")+')\n'+req.params.get('version_comment', ''))
                    pass


                if req.params.get("change_file")=="attfile" and not create_version_error: # add file as attachment
                    if attpath=="":
                        # no attachment directory existing
                        file = importFile(uploadfile.filename, uploadfile.tempname) # add new file
                        file.mimetype = "inode/file"
                        file.type = "attachment"
                        node.addFile(file)
                    else:
                        # import attachment file into existing attachment directory
                        file = importFileIntoDir(getImportDir() + "/" + attpath, uploadfile.tempname) # add new file
                    node.set("system.version.comment", '('+t(req, "edit_files_new_version_attachment_comment")+')\n'+req.params.get('version_comment', ''))
                    pass

        elif op == "addthumb":  # create new thumbanil from uploaded file
            uploadfile = req.params.get("updatefile")

            if uploadfile:
                thumbname = os.path.join(getImportDir(), hashlib.md5(str(random.random())).hexdigest()[0:8]) + ".thumb"

                file = importFile(thumbname, uploadfile.tempname)  # add new file
                makeThumbNail(file.retrieveFile(), thumbname)
                makePresentationFormat(file.retrieveFile(), thumbname + "2")

                if os.path.exists(file.retrieveFile()):  # remove uploaded original
                    os.remove(file.retrieveFile())

                for f in node.getFiles():
                    if f.type in ["thumb", "presentation", "presentati"]:
                        if os.path.exists(f.retrieveFile()):
                            os.remove(f.retrieveFile())
                        node.removeFile(f)

                node.addFile(tree.FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                node.addFile(tree.FileNode(name=thumbname + "2", type="presentation", mimetype="image/jpeg"))
                logging.getLogger('usertracing').info(user.name + " changed thumbnail of node " + node.id)

        elif op == "postprocess":
            if hasattr(node, "event_files_changed"):
                try:
                    node.event_files_changed()
                    logging.getLogger('usertracing').info(user.name + " postprocesses node " + node.id)
                except:
                    update_error = True

    v = {"id": req.params.get("id", "0"), "tab": req.params.get("tab", ""), "node": node, "update_error": update_error,
         "user": user, "files": filter(lambda x: x.type != 'statistic', node.getFiles()),
         "statfiles": filter(lambda x: x.type == 'statistic', node.getFiles()),
         "attfiles": filter(lambda x: x.type == 'attachment', node.getFiles()), "att": [], "nodes": [node], "access": access}

    for f in v["attfiles"]:  # collect all files in attachment directory
        if f.getMimeType() == "inode/directory":
            for root, dirs, files in os.walk(f.retrieveFile()):
                for name in files:
                    af = tree.FileNode(root + "/" + name, "attachmentfile", getMimeType(name)[0])
                    v["att"].append(af)

    return req.getTAL("web/edit/modules/files.html", v, macro="edit_files_file")
