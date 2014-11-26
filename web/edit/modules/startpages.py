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
import sys
import json

import logging
import core.users as users
import core.config as config

from utils.utils import format_filesize
from core.translation import lang
from core.acl import AccessData
from core.tree import FileNode
from web.edit.edit_common import send_nodefile_tal, upload_for_html


def getContent(req, ids):
    node = tree.getNode(ids[0])
    if req.params.get('file') == "config":  # configuration file for ckeditor
        req.reply_headers['Content-Type'] = "application/javascript"
        return req.writeTAL("web/edit/modules/startpages.html", {'id': ids[0], 'lang': lang(req)}, macro="ckconfig")

    if "action" in req.params:
        if req.params.get('action') == "getfile":  # deliver filecontent
            data = ""
            for f in [f for f in node.getFiles() if f.mimetype == "text/html"]:
                filepath = f.retrieveFile().replace(config.get("paths.datadir"), '')
                if req.params.get('filename') == filepath and os.path.exists(config.get("paths.datadir") + filepath):
                    with open(config.get("paths.datadir") + filepath, "r") as fil:
                        data = fil.read()
                    break
            req.write(json.dumps({'filecontent': data}))
        if req.params.get('action') == "save":  # save filedata
            if req.params.get('filename') == "add":  # add new file
                maxid = 0
                for f in [f for f in node.getFiles() if f.type == "content"]:
                    if int(f.retrieveFile()[:-5].split("_")[-1]) >= maxid:
                        maxid = int(f.retrieveFile()[:-5].split("_")[-1]) + 1
                filename = 'html/%s_%s.html' % (req.params.get('id'), maxid)
                with open(config.get("paths.datadir") + filename, "w") as fil:
                    fil.write(req.params.get('data'))
                node.addFile(FileNode(filename, "content", "text/html"))
                req.write(json.dumps({'filename': '', 'state': 'ok'}))
                return None
            else:
                for f in [f for f in node.getFiles() if f.mimetype == "text/html"]:
                    filepath = f.retrieveFile().replace(config.get("paths.datadir"), '')
                    if req.params.get('filename') == filepath and os.path.exists(config.get("paths.datadir") + filepath):
                        with open(config.get("paths.datadir") + filepath, "w") as fil:
                            fil.write(req.params.get('data'))
                        req.write(json.dumps(
                            {'filesize': format_filesize(os.path.getsize(config.get("paths.datadir") + filepath)),
                             'filename': req.params.get('filename'), 'state': 'ok'}))
                        break
        return None

    if "option" in req.params:
        if req.params.get("option") == "filebrowser":  # open filebrowser
            req.write(send_nodefile_tal(req))
            return ""

        if req.params.get("option") == "htmlupload":  # use fileupload
            req.write(upload_for_html(req))
            return ""

        if "delete" in req.params:  # delete file via fck
            for f in node.getFiles():
                if f.retrieveFile().endswith(req.params.get('option')):
                    if os.path.exists(f.retrieveFile()):
                        os.remove(f.retrieveFile())
                        node.removeFile(f)
                    break
            return ""

    user = users.getUserFromRequest(req)
    access = AccessData(req)

    if access.hasWriteAccess(node):

        for key in req.params.keys():
            if key.startswith("delete_"):  # delete page
                page = key[7:-2]
                try:
                    file_shortpath = page.replace(config.get("paths.datadir"), "")
                    if os.path.exists(page):
                        os.remove(page)
                    filenode = FileNode(page, "", "text/html")

                    node.removeAttribute("startpagedescr." + file_shortpath)
                    node.set("startpage.selector", node.get("startpage.selector").replace(file_shortpath, ""))
                    node.removeFile(filenode)
                    logging.getLogger('usertracing').info(
                        user.name + " - startpages - deleted FileNode and file for node %s (%s): %s, %s, %s, %s" % (
                            node.id, node.name, page, filenode.getName(), filenode.type, filenode.mimetype))
                except:
                    logging.getLogger('usertracing').error(user.name + " - startpages - error while delete FileNode and file for " + page)
                    logging.getLogger('usertracing').error("%s - %s" % (sys.exc_info()[0], sys.exc_info()[1]))
                break

        if "save_page" in req.params:  # save page
            content = ""
            for key in req.params.keys():
                if key.startswith("page_content"):
                    content = req.params.get(key, "")
                    break

            with open(req.params.get('file_path'), "w") as fi:
                fi.writelines(content)

            del req.params['save_page']
            del req.params['file_to_edit']
            req.params['tab'] = 'startpages'
            return getContent(req, [node.id])

        if "cancel_page" in req.params:
            del req.params['file_to_edit']
            del req.params['cancel_page']
            return getContent(req, [node.id])

    if not access.hasWriteAccess(node) or "editor" in users.getHideMenusForUser(user):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    filelist = []
    for f in node.getFiles():
        if f.mimetype == 'text/html' and f.getType() in ['content']:
            filelist.append(f)

    languages = [language.strip() for language in config.get("i18n.languages").split(",")]

    if "startpages_save" in req.params.keys():
        sidebar = ""
        for k in [k for k in req.params if k.startswith('sidebar_')]:
            sidebar += "%s:%s;" % (k[8:], req.params[k])
        node.set('system.sidebar', sidebar)

        for k in [k for k in req.params if k.startswith('descr.')]:
            node.set('startpage' + k, req.params[k])

        # build startpage_selector
        startpage_selector = ""
        for language in languages:
            startpage_selector += "%s:%s;" % (language, req.params.get('radio_' + language))
        node.set('startpage.selector', startpage_selector[0:-1])

    named_filelist = []

    for f in filelist:
        long_path = f.retrieveFile()
        short_path = long_path.replace(config.get("paths.datadir"), '')

        file_exists = os.path.isfile(long_path)
        file_size = "-"
        if file_exists:
            file_size = os.path.getsize(long_path)

        langlist = []
        sidebar = []
        for language in languages:
            spn = node.getStartpageFileNode(language)
            if spn and spn.retrieveFile() == long_path:
                langlist.append(language)
            if node.get('system.sidebar').find(language + ":" + short_path) >= 0:
                sidebar.append(language)

        named_filelist.append((short_path,
                               node.get('startpagedescr.' + short_path),
                               f.type,
                               f,
                               file_exists,
                               format_filesize(file_size),
                               long_path,
                               langlist,
                               "/file/%s/%s" % (req.params.get("id", "0"), short_path.split('/')[-1]),
                               sidebar))
    lang2file = node.getStartpageDict()

    # compatibility: there may be old startpages in the database that
    # are not described by node attributes
    initial = filelist and not lang2file

    # node may not have startpage set for some language
    # compatibilty: node may not have attribute startpage.selector
    # build startpage_selector and wriote back to node
    startpage_selector = ""
    for language in languages:
        if initial:
            lang2file[language] = named_filelist[0][0]
        else:
            lang2file[language] = lang2file.setdefault(language, '')
        startpage_selector += "%s:%s;" % (language, lang2file[language])

    node.set('startpage.selector', startpage_selector[0:-1])

    v = {"id": req.params.get("id", "0"), "tab": req.params.get("tab", ""), "node": node,
         "named_filelist": named_filelist, "languages": languages, "lang2file": lang2file, "types": ['content'],
         "d": lang2file and True}

    return req.getTAL("web/edit/modules/startpages.html", v, macro="edit_startpages")
