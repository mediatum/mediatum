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
import json
import codecs

import logging
import core.config as config

from utils.utils import format_filesize, dec_entry_log
from core.translation import lang
from web.edit.edit_common import send_nodefile_tal, upload_for_html
from core.transition import httpstatus, current_user
from core import Node
from core import db
from core import File

q = db.query
logg = logging.getLogger(__name__)


@dec_entry_log
def getContent(req, ids):
    node = q(Node).get(ids[0])
    user = current_user
    if not node.has_write_access() or "editor" in user.hidden_edit_functions:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if req.params.get('file') == "config":  # configuration file for ckeditor
        req.reply_headers['Content-Type'] = "application/javascript"
        return req.writeTAL("web/edit/modules/startpages.html", {'id': ids[0], 'lang': lang(req)}, macro="ckconfig")

    if "action" in req.params:
        if req.params.get('action') == "getfile":  # deliver filecontent
            data = ""
            for f in [f for f in node.files if f.mimetype == "text/html"]:
                filepath = f.abspath.replace(config.get("paths.datadir"), '')
                if req.params.get('filename') == filepath and os.path.exists(config.get("paths.datadir") + filepath):
                    with codecs.open(config.get("paths.datadir") + filepath, "r", encoding='utf8') as fil:
                        data = fil.read()
                    logg.info("%s opened startpage %s for node %s (%s, %s)", user.login_name, filepath, node.id, node.name, node.type)
                    break
            req.write(json.dumps({'filecontent': data}, ensure_ascii=False))
        if req.params.get('action') == "save":  # save filedata
            if req.params.get('filename') == "add":  # add new file
                maxid = 0
                for f in [f for f in node.files if f.type == "content"]:
                    try:
                        if int(f.abspath[:-5].split("_")[-1]) >= maxid:
                            maxid = int(f.abspath[:-5].split("_")[-1]) + 1
                    except ValueError:
                        pass
                filename = 'html/%s_%s.html' % (req.params.get('id'), maxid)
                while os.path.exists(config.get("paths.datadir") + filename):
                    maxid = maxid + 1
                    filename = 'html/%s_%s.html' % (req.params.get('id'), maxid)
                with codecs.open(config.get("paths.datadir") + filename, "w", encoding='utf8') as fil:
                    fil.write(req.params.get('data'))
                node.files.append(File(filename, u"content", u"text/html"))
                db.session.commit()
                req.write(json.dumps({'filename': '', 'state': 'ok'}))
                logg.info("%s added startpage %s for node %s (%s, %s)", user.login_name, filename, node.id, node.name, node.type)
                return None
            else:
                for f in [f for f in node.files if f.mimetype == "text/html"]:
                    filepath = f.abspath.replace(config.get("paths.datadir"), '')
                    if req.params.get('filename') == filepath and os.path.exists(config.get("paths.datadir") + filepath):
                        with open(config.get("paths.datadir") + filepath, "w") as fil:
                            fil.write(req.params.get('data'))
                        req.write(json.dumps(
                            {'filesize': format_filesize(os.path.getsize(config.get("paths.datadir") + filepath)),
                             'filename': req.params.get('filename'), 'state': 'ok'}, ensure_ascii=False))
                        logg.info("%s saved startpage %s for node %s (%s, %s)", user.login_name, filepath, node.id, node.name, node.type)
                        break
        return None

    if "option" in req.params:
        if req.params.get("option") == "filebrowser":  # open filebrowser
            logg.info("%s opening ckeditor filebrowser for node %s (%r, %r)", user.login_name, node.id, node.name, node.type)
            req.write(send_nodefile_tal(req))
            return ""

        if req.params.get("option") == "htmlupload":  # use fileupload
            logg.info("%s going to use ckeditor fileupload (htmlupload) for node %s (%s, %s)",
                      user.login_name, node.id, node.name, node.type)
            req.write(upload_for_html(req))
            return ""

        if "delete" in req.params:  # delete file via CKeditor
            for f in node.files:
                if f.abspath.endswith(req.params.get('option')):
                    filepath = f.abspath.replace(config.get("paths.datadir"), '')
                    logg.info("%s going to delete ckeditor filebrowser file %s for node %s (%s, %s)",
                              user.login_name, filepath, node.id, node.name, node.type)
                    if os.path.exists(f.abspath):
                        os.remove(f.abspath)
                        node.files.remove(f)
                    break
            db.session.commit()
            return ""

    for key in req.params.keys():
        if key.startswith("delete_"):  # delete page
            page = key[7:-2]
            try:
                file_shortpath = page.replace(config.get("paths.datadir"), "")
                fullpath = os.path.join(config.get("paths.datadir"), page)
                if os.path.exists(fullpath):
                    os.remove(fullpath)
                    logg.info("%s removed file %s from disk", user.login_name, fullpath)
                else:
                    logg.warn("%s could not remove file %s from disk: not existing", user.login_name, fullpath)
                filenode = q(File).filter_by(path=page, mimetype=u"text/html").one()
                try:
                    del node.system_attrs["startpagedescr." + file_shortpath]
                except KeyError:
                    pass
                node.system_attrs["startpage_selector"] = node.system_attrs["startpage_selector"].replace(file_shortpath, "")
                node.files.remove(filenode)
                db.session.commit()
                logg.info("%s - startpages - deleted File and file for node %s (%s): %s, %s, %s, %s",
                        user.login_name, node.id, node.name, page, filenode.path, filenode.filetype, filenode.mimetype)
            except:
                logg.exception("%s - startpages - error while delete File and file for %s, exception ignored", user.login_name, page)
            break

    if "save_page" in req.params:  # save page
        content = ""
        for key in req.params.keys():
            if key.startswith("page_content"):
                content = req.params.get(key, "")
                break

        with open(req.params.get('file_path'), "w", encoding='utf8') as fi:
            fi.writelines(content)

        del req.params['save_page']
        del req.params['file_to_edit']
        req.params['tab'] = 'startpages'
        return getContent(req, [node.id])

    if "cancel_page" in req.params:
        del req.params['file_to_edit']
        del req.params['cancel_page']
        return getContent(req, [node.id])

    filelist = []
    for f in node.files:
        if f.mimetype == 'text/html' and f.getType() in ['content']:
            filelist.append(f)

    db.session.commit()

    if "startpages_save" in req.params.keys():  # user saves startpage configuration
        logg.info("%s going to save startpage configuration for node %s (%s, %s): %s",
                  user.login_name, node.id, node.name, node.type, req.params)

        sidebar = ""
        for k in [k for k in req.params if k.startswith('sidebar_')]:
            sidebar += "%s:%s;" % (k[8:], req.params[k])
        node.set('system.sidebar', sidebar)

        for k in [k for k in req.params if k.startswith('descr.')]:
            node.system_attrs['startpage' + k] = req.params[k]

        # build startpage_selector
        startpage_selector = ""
        for language in config.languages:
            startpage_selector += "%s:%s;" % (language, req.params.get('radio_' + language))
        node.system_attrs['startpage_selector'] = startpage_selector[0:-1]
    named_filelist = []

    for f in filelist:
        long_path = f.abspath
        short_path = long_path.replace(config.get("paths.datadir"), '')

        file_exists = os.path.isfile(long_path)
        file_size = "-"
        if file_exists:
            file_size = os.path.getsize(long_path)

        langlist = []
        sidebar = []
        for language in config.languages:
            spn = node.getStartpageFileNode(language)
            if spn and spn.abspath == long_path:
                langlist.append(language)
            if node.system_attrs.get('sidebar', '').find(language + ":" + short_path) >= 0:
                sidebar.append(language)

        named_filelist.append((short_path,
                               node.system_attrs.get('startpagedescr.' + short_path),
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
    # compatibilty: node may not have system attribute startpage_selector
    # build startpage_selector and write back to node
    startpage_selector = ""
    for language in config.languages:
        if initial:
            lang2file[language] = named_filelist[0][0]
        else:
            lang2file[language] = lang2file.setdefault(language, '')
        startpage_selector += "%s:%s;" % (language, lang2file[language])

    node.system_attrs['startpage_selector'] = startpage_selector[0:-1]

    db.session.commit()

    v = {"id": req.params.get("id", "0"),
         "tab": req.params.get("tab", ""),
         "node": node,
         "named_filelist": named_filelist,
         "languages": config.languages,
         "lang2file": lang2file,
         "types": ['content'],
         "d": lang2file and True}

    return req.getTAL("web/edit/modules/startpages.html", v, macro="edit_startpages")
