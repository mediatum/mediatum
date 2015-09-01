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

import os
import core.users as users
import logging
import core.acl as acl
from utils.utils import getMimeType, get_user_id
from utils.fileutils import importFile, getImportDir, importFileIntoDir
from contenttypes.image import makeThumbNail, makePresentationFormat
from core.transition import httpstatus
from core.translation import t
from core import Node
from core import db
from core import File
from contenttypes import Home, Collections
from core.systemtypes import Root
from core.users import user_from_session

q = db.query
logg = logging.getLogger(__name__)


def _finish_change(node, change_file, user, uploadfile, req):

    if change_file == "yes":  # remove old files
        for f in node.files:
            if f.filetype in node.getSysFiles():
                node.files.remove(f)

    if change_file in ["yes", "no"]:
        importFile(uploadfile.filename, uploadfile.tempname)  # add new file
        node.files.append(file)
        logg.info("%s changed file of node %s to %s (%s)", user.login_name, node.id, uploadfile.filename, uploadfile.tempname)

    attpath = ""
    for f in node.files:
        if f.mimetype == "inode/directory":
            attpath = f.base_name
            break

    if change_file == "attdir":  # add attachmentdir
        if attpath == "":  # add attachment directory
            attpath = req.params.get("inputname")
            if not os.path.exists(getImportDir() + "/" + attpath):
                os.mkdir(getImportDir() + "/" + attpath)
                node.files.append(File(getImportDir() + "/" + attpath, "attachment", "inode/directory"))

            importFileIntoDir(getImportDir() + "/" + attpath, uploadfile.tempname)  # add new file

    if change_file == "attfile":  # add file as attachment
        if attpath == "":
            # no attachment directory existing
            file = importFile(uploadfile.filename, uploadfile.tempname)  # add new file
            file.mimetype = "inode/file"
            file.type = "attachment"
            node.files.append(file)
        else:
            # import attachment file into existing attachment directory
            importFileIntoDir(getImportDir() + "/" + attpath, uploadfile.tempname)  # add new file


def _handle_change(node, req):
    uploadfile = req.params.get("updatefile")

    if not uploadfile:
        return
    change_file = req.params.get("change_file")
    user = user_from_session(req.session)

    if (req.params.get('generate_new_version') and not hasattr(node, "metaFields")):
        # Create new version when changing files
        version_comment = req.params.get('version_comment', '').strip()
        if not version_comment or version_comment == '&nbsp;':
            # comment must be given, abort
            req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
            return req.getTAL("web/edit/modules/files.html", {}, macro="version_error")
        else:
            if change_file == "yes":
                translation_msg_id = "edit_files_new_version_exchanging_comment"
            elif change_file == "no":
                translation_msg_id = "edit_files_new_version_adding_comment"
            elif change_file == "attdir":
                translation_msg_id = "edit_files_new_version_attachment_directory_comment"
            elif change_file == "attfile":
                translation_msg_id = "edit_files_new_version_attachment_comment"

            version_comment_full = u'({})\n{}'.format(t(req, translation_msg_id), version_comment)

            with node.new_tagged_version(comment=version_comment_full):
                node.set("updateuser", user.login_name)
                _finish_change(node, change_file, user, uploadfile, req)

            req.setStatus(httpstatus.HTTP_MOVED_TEMPORARILY)
            return req.getTAL("web/edit/modules/metadata.html", {'url': '?id={}&tab=files'.format(node.id), 'pid': None}, macro="redirect")
    else:
        # no new version
        _finish_change(node, change_file, user, uploadfile, req)


def getContent(req, ids):
    ret = ""
    user = users.getUserFromRequest(req)
    node = q(Node).get(ids[0])
    update_error = False
    access = acl.AccessData(req)

    logg.debug("%s|web.edit.modules.files.getContend|req.fullpath=%s|req.path=%s|req.params=%s|ids=%s",
               get_user_id(req), req.fullpath, req.path, req.params, ids)

    if not access.hasWriteAccess(node) or "files" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if 'data' in req.params:
        if req.params.get('data') == 'children':  # get formated list of childnodes of selected directory
            req.writeTAL("web/edit/modules/files.html", {'children': node.children}, macro="edit_files_popup_children")

        if req.params.get('data') == 'additems':  # add selected node as children
            for childid in req.params.get('items').split(";"):
                if childid.strip() != "":
                    childnode = q(Node).get(childid.strip())
                    for p in childnode.parents:
                        p.children.remove(childnode)
                    node.children.append(childnode)
            req.writeTAL("web/edit/modules/files.html", {'children': node.children, 'node': node}, macro="edit_files_children_list")

        if req.params.get('data') == 'removeitem':  # remove selected childnode node
            try:
                remnode = q(Node).get(req.params.get('remove'))
                if len(remnode.parents) == 1:
                    users.getUploadDir(user).children.append(remnode)
                node.children.remove(remnode)
            except:  # node not found
                logg.exception("exception in getContent, node not found? ignore")
                pass

            req.writeTAL("web/edit/modules/files.html", {'children': node.children, 'node': node}, macro="edit_files_children_list")

        if req.params.get('data') == 'reorder':
            i = 0
            for id in req.params.get('order').split(","):
                if id != "":
                    n = q(Node).get(id)
                    n.setOrderPos(i)
                    i += 1

        if req.params.get('data') == 'translate':
            req.writeTALstr('<tal:block i18n:translate="" tal:content="msgstr"/>', {'msgstr': req.params.get('msgstr')})

        db.session.commit()
        return ""

    if req.params.get("style") == "popup":
        v = {"basedirs": [q(Home).one(), q(Collections).one()]}
        id = req.params.get("id", q(Root).one().id)
        v["script"] = "var currentitem = '%s';\nvar currentfolder = '%s';\nvar node = %s;" % (id, req.params.get('parent'), id)
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
                    for file in node.files:
                        if file.base_name == filename[1] and file.type == filename[0]:
                            # remove all files in directory
                            if file.mimetype == "inode/directory":
                                for root, dirs, files in os.walk(file.abspath):
                                    for name in files:
                                        try:
                                            os.remove(root + "/" + name)
                                        except:
                                            logg.exception("exception while removing file, ignore")
                                    os.removedirs(file.abspath + "/")
                            node.files.remove(file)
                            try:
                                os.remove(file.abspath)
                            except:
                                pass

                            break
                    break
                elif key.startswith("delatt|"):
                    for file in node.files:
                        if file.mimetype == "inode/directory":
                            try:
                                os.remove(file.abspath + "/" + key.split("|")[2][:-2])
                            except:
                                logg.exception("exception while removing file, ignore")
                            break
                    break

        elif op == "change":
            _handle_change(node, req)

        elif op == "addthumb":  # create new thumbanil from uploaded file
            uploadfile = req.params.get("updatefile")

            if uploadfile:
                thumbname = os.path.join(getImportDir(), hashlib.md5(ustr(random.random())).hexdigest()[0:8]) + ".thumb"

                file = importFile(thumbname, uploadfile.tempname)  # add new file
                makeThumbNail(file.abspath, thumbname)
                makePresentationFormat(file.abspath, thumbname + "2")

                if os.path.exists(file.abspath):  # remove uploaded original
                    os.remove(file.abspath)

                for f in node.files:
                    if f.type in ["thumb", "presentation", "presentati"]:
                        if os.path.exists(f.abspath):
                            os.remove(f.abspath)
                        node.files.remove(f)

                node.files.append(File(thumbname, "thumb", "image/jpeg"))
                node.files.append(File(thumbname + "2", "presentation", "image/jpeg"))
                logg.info("%s changed thumbnail of node %s", user.login_name, node.id)

        elif op == "postprocess":
            if hasattr(node, "event_files_changed"):
                try:
                    node.event_files_changed()
                    logg.info("%s postprocesses node %s", user.login_name, node.id)
                except:
                    update_error = True

    db.session.commit()

    v = {"id": req.params.get("id", "0"),
         "tab": req.params.get("tab", ""),
         "node": node,
         "update_error": update_error,
         "user": user,
         "files": filter(lambda x: x.type != 'statistic', node.files),
         "statfiles": filter(lambda x: x.type == 'statistic', node.files),
         "attfiles": filter(lambda x: x.type == 'attachment', node.files),
         "att": [],
         "nodes": [node],
         "access": access}

    for f in v["attfiles"]:  # collect all files in attachment directory
        if f.mimetype == "inode/directory":
            for root, dirs, files in os.walk(f.abspath):
                for name in files:
                    af = File(root + "/" + name, "attachmentfile", getMimeType(name)[0])
                    v["att"].append(af)

    return req.getTAL("web/edit/modules/files.html", v, macro="edit_files_file")
