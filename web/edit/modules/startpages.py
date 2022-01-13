# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import os
import json
import codecs

import logging
import collections as _collections
import operator as _operator
import core.config as config
import mediatumtal.tal as _tal

from utils.utils import format_filesize, suppress
from core.translation import lang
from web.edit.edit_common import send_nodefile_tal, upload_for_html
from core.users import user_from_session as _user_from_session
from core import httpstatus
from core import Node
from core import db
from core import File

q = db.query
logg = logging.getLogger(__name__)


_NamedFile = _collections.namedtuple(
    "_NamedFile",
    "short_path description file_size language_list technical_name"
    )


def _get_named_filelist(node, id_from_req):
    files = []
    for f in node.files:
        if f.mimetype != 'text/html' or f.getType() != 'content':
            continue

        short_path = os.path.relpath(f.abspath, config.get("paths.datadir"))
        assert not short_path.startswith("../"), "file absolute path not in data dir"

        langlist = []
        for language in config.languages:
            spn = node.getStartpageFileNode(language)
            if spn and spn.abspath == f.abspath:
                langlist.append(language)

        files.append(
            _NamedFile(
                short_path=short_path,
                description=node.system_attrs.get('startpagedescr.' + short_path),
                file_size=format_filesize(os.path.getsize(f.abspath) if os.path.isfile(f.abspath) else "-"),
                language_list=tuple(langlist),
                technical_name=os.path.join("/file", str(id_from_req), short_path.split('/')[-1]),
            )
        )

    files.sort(key=_operator.attrgetter("description"))
    return files


def getContent(req, ids):
    node = q(Node).get(ids[0])
    user = _user_from_session()
    if not node.has_write_access() or "editor" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if req.values.get('file') == "config":  # configuration file for ckeditor
        req.response.content_type = "application/javascript"
        req.response.set_data(_tal.processTAL({'id': ids[0], 'lang': lang(req)}, file="web/edit/modules/startpages.html", macro="ckconfig", request=req))
        return

    if "action" in req.values:
        if req.values['action'] == "getfile":  # deliver filecontent
            data = ""
            for f in [f for f in node.files if f.mimetype == "text/html"]:
                filepath = f.abspath.replace(config.get("paths.datadir"), '')
                if req.values.get('filename') == filepath and os.path.exists(config.get("paths.datadir") + filepath):
                    with codecs.open(config.get("paths.datadir") + filepath, "r", encoding='utf8') as fil:
                        data = fil.read()
                    logg.info("%s opened startpage %s for node %s (%s, %s)", user.login_name, filepath, node.id, node.name, node.type)
                    break
            req.response.set_data(json.dumps({'filecontent': data}, ensure_ascii=False))
            req.response.mimetype = 'application/json'

        if req.values['action'] == "save":  # save filedata
            if req.values.get('filename') == "add":  # add new file
                maxid = 0
                for f in [f for f in node.files if f.type == "content"]:
                    with suppress(ValueError, warn=False):
                        if int(f.abspath[:-5].split("_")[-1]) >= maxid:
                            maxid = int(f.abspath[:-5].split("_")[-1]) + 1
                filename = 'html/{}_{}.html'.format(req.values['id'], maxid)
                while os.path.exists(config.get("paths.datadir") + filename):
                    maxid = maxid + 1
                    filename = 'html/{}_{}.html'.format(req.values['id'], maxid)
                with codecs.open(config.get("paths.datadir") + filename, "w", encoding='utf8') as fil:
                    fil.write(req.values['data'])
                node.files.append(File(filename, u"content", u"text/html"))
                db.session.commit()
                logg.info("%s added startpage %s for node %s (%s, %s)", user.login_name, filename, node.id, node.name, node.type)
            else:
                for f in [f for f in node.files if f.mimetype == "text/html"]:
                    filepath = f.abspath.replace(config.get("paths.datadir"), '')
                    if req.values.get('filename') == filepath and os.path.exists(config.get("paths.datadir") + filepath):
                        with open(config.get("paths.datadir") + filepath, "w") as fil:
                            try:
                                fil.write(req.values.get('data'))
                            except UnicodeEncodeError:
                                # some unicode characters like 'Black Circle' &#9679; are not translated in the
                                # html entity by the current ckeditor version
                                fil.write(req.values.get('data').encode('ascii', 'xmlcharrefreplace'))

                        logg.info("%s saved startpage %s for node %s (%s, %s)", user.login_name, filepath, node.id, node.name, node.type)
                        break

            req.response.set_data(_tal.processTAL(
                dict(
                    named_filelist=_get_named_filelist(node, req.values.get("id", "0")),
                    languages=config.languages,
                ),
                file="web/edit/modules/startpages.html",
                macro="named_filelist",
                request=req,
            ))
        return

    if "option" in req.values:
        if req.values["option"] == "filebrowser":  # open filebrowser
            logg.info("%s opening ckeditor filebrowser for node %s (%r, %r)", user.login_name, node.id, node.name, node.type)
            req.response.set_data(send_nodefile_tal(req))
            return ""

        if req.values["option"] == "htmlupload":  # use fileupload
            logg.info("%s going to use ckeditor fileupload (htmlupload) for node %s (%s, %s)",
                      user.login_name, node.id, node.name, node.type)
            req.response.set_data(upload_for_html(req))
            return ""

        if "delete" in req.values:  # delete file via CKeditor
            for f in node.files:
                if f.abspath.endswith(req.values['option']):
                    filepath = f.abspath.replace(config.get("paths.datadir"), '')
                    logg.info("%s going to delete ckeditor filebrowser file %s for node %s (%s, %s)",
                              user.login_name, filepath, node.id, node.name, node.type)
                    if os.path.exists(f.abspath):
                        os.remove(f.abspath)
                        node.files.remove(f)
                    break
            db.session.commit()
            return ""

    for key in req.values:
        if not key.startswith("delete_"):  # delete page
            continue
        page = req.values[key]
        try:
            filenode = q(File).filter_by(path=page, mimetype=u"text/html").one()
            if filenode not in node.files:
                logg.error(
                    "%s - startpages - error while delete File and file for %s that does not belong to node %d",
                    user.login_name, page, node.id,
                )
                break
            file_shortpath = page.replace(config.get("paths.datadir"), "")
            fullpath = os.path.join(config.get("paths.datadir"), page)
            if os.path.exists(fullpath):
                os.remove(fullpath)
                logg.info("%s removed file %s from disk", user.login_name, fullpath)
            else:
                logg.warning("%s could not remove file %s from disk: not existing", user.login_name, fullpath)
            with suppress(KeyError, warn=False):
                del node.system_attrs["startpagedescr." + file_shortpath]
            node.system_attrs["startpage_selector"] = node.system_attrs["startpage_selector"].replace(file_shortpath, "")
            node.files.remove(filenode)
            q(File).filter_by(id=filenode.id).delete()
            db.session.commit()

            logg.info("%s - startpages - deleted File and file for node %s (%s): %s, %s, %s, %s",
                    user.login_name, node.id, node.name, page, filenode.path, filenode.filetype, filenode.mimetype)
            req.response.set_data(_tal.processTAL(
                    dict(
                        named_filelist=_get_named_filelist(node, req.values.get("id", "0")),
                        languages=config.languages,
                        ),
                    file="web/edit/modules/startpages.html",
                    macro="named_filelist",
                    request=req,
                ))
            return
        except:
            logg.exception("%s - startpages - error while delete File and file for %s, exception ignored", user.login_name, page)
        break

    if "startpages_save" in req.values:  # user saves startpage configuration
        logg.info("%s going to save startpage configuration for node %s (%s, %s): %s",
                  user.login_name, node.id, node.name, node.type, req.values)

        for k in [k for k in req.values if k.startswith('descr.')]:
            node.system_attrs['startpage' + k] = req.values[k]

        # build startpage_selector
        startpage_selector = ""
        for language in config.languages:
            startpage_selector += "%s:%s;" % (language, req.values.get('radio_' + language))
        node.system_attrs['startpage_selector'] = startpage_selector[0:-1]
        db.session.commit()

    named_filelist = _get_named_filelist(node, req.values.get("id", "0"))
    lang2file = {lang: "" for lang in config.languages}
    lang2file.update(node.getStartpageDict())

    return _tal.processTAL(
            dict(
                id=req.values.get("id", "0"),
                tab=req.values.get("tab", ""),
                node=node,
                named_filelist=named_filelist,
                languages=config.languages,
                lang2file=lang2file,
                types=['content'],
                d=lang2file and True,
                csrf=req.csrf_token.current_token,
            ),
            file="web/edit/modules/startpages.html",
            macro="edit_startpages",
            request=req,
        )
