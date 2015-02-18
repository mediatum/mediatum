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
import logging
import sys
import os
import codecs
import core.config as config
import core
import core.tree as tree

from version import mediatum_version
from utils.utils import format_filesize
from core.transition import httpstatus

logg = logging.getLogger(__name__)


def getInformation():
    return {"version": "1.0", "required": 1}


def validate(req, op):
    return view(req)


def searchconfig_action(req):
    for key in req.params.keys():
        if key.startswith("delete|"):
            logg.debug("delete key %s %s", "for section", key.split("|"), req.params.get("section"))
            break


def view(req):

    gotopage = req.params.get("gotopage", "")
    if gotopage == "searchconfig":
        searchconfig_action(req)

    page = req.params.get("page", "")
    gotopage = req.params.get("gotopage", "")

    v = {}

    v["gotopage"] = req.params.get("gotopage", "")
    v["subitem"] = req.params.get("editsubitem", "")

    if page == "python":
        # python information
        v['copyright'] = sys.copyright
        v['platform'] = sys.platform
        v['version'] = sys.version
        v['platform'] = sys.platform

        if sys.platform.startswith("win"):
            v['plat_version'] = sys.getwindowsversion()
        else:
            v['plat_version'] = ''

        return req.getTAL("web/admin/modules/settings.html", v, macro="view_python")

    elif page == "mediatum":
        # mediatum information
        with codecs.open(os.path.join(config.basedir, 'mediatum.cfg'), "rb", encoding='utf8') as fi:
            v['mediatum_cfg'] = fi.readlines()
            v["mediatum_version"] = mediatum_version

        return req.getTAL("web/admin/modules/settings.html", v, macro="view_mediatum")

    elif page == "database":
        if config.get("database.type") == "sqlite":
            # sqlite
            v['db_driver'] = 'PySQLite'
            v['db_connector_version'] = 'n.a.'
        else:
            # mysql
            import MySQLdb
            v['db_driver'] = 'MySQLdb'
            v['db_connector_version'] = ('%i.%i.%i %s %i' % MySQLdb.version_info)

        from core.tree import db
        v['db_status'] = db.getStatus()
        v['db_size'] = format_filesize(db.getDBSize())

        return req.getTAL("web/admin/modules/settings.html", v, macro="view_database")

    elif page == "search":
        # search
        if config.get("config.searcher") == "fts3":
            v['search_driver'] = 'sqlite with fts3 support'

        else:
            v['search_driver'] = 'magpy'

        from core.tree import searcher
        v['search_info'] = searcher.getSearchInfo()
        v['search_size'] = format_filesize(searcher.getSearchSize())

        return req.getTAL("web/admin/modules/settings.html", v, macro="view_search")

    elif page == "searchconfig":
        node = tree.getRoot()
        file = None
        sections = ["chars", "words"]
        data = {"chars": [], "words": []}
        for f in node.getFiles():
            if f.retrieveFile().endswith("searchconfig.txt"):
                file = f
                break

        if file and os.path.exists(file.retrieveFile()):
            section = ""
            for line in codecs.open(file.retrieveFile(), "r", encoding='utf8'):
                line = line[:-1]
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    continue
                if section in sections:
                    data[section].append(line.split("="))

        v["data"] = data

        return req.getTAL("web/admin/modules/settings.html", v, macro="view_searchconfig")

    elif page == "archive":
        try:
            v['a_managers'] = core.archivemanager.getManager()
        except:
            logg.exception("exception in settings / archive")
            req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
            return req.getTAL("web/admin/modules/settings.html", v, macro="view_error")

        v['archive_interval'] = config.get('archive.interval')
        v['archive_activated'] = config.get('archive.activate')
        return req.getTAL("web/admin/modules/settings.html", v, macro="view_archive")

    else:
        return req.getTAL("web/admin/modules/settings.html", v, macro="view")
