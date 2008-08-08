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

import sys
import os
import core.config as config

from version import mediatum_version
from core.config import basedir
from utils.utils import format_filesize

def validate(req, op):
    return view(req)


def view(req):
    global basedir
    v = {}

    # python information
    v['copyright'] = sys.copyright
    v['platform'] = sys.platform
    v['version'] = sys.version
    v['platform'] = sys.platform

    if sys.platform.startswith("win"):
        v['plat_version'] = sys.getwindowsversion()
    else:
        v['plat_version'] = ''

    # mediatum information
    fi = open(os.path.join(basedir,'mediatum.cfg'), "rb")
    v['mediatum_cfg'] = fi.readlines()
    v["mediatum_version"] = mediatum_version
    
    if config.get("database.type")=="sqlite":
        #sqlite
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


    # search
    if config.get("config.searcher")=="fts3":
        v['search_driver'] = 'sqlite with fts3 support'
        
        
    else:
        v['search_driver'] = 'magpy'
        
    from core.tree import searcher
    v['search_info'] = searcher.getSearchInfo()
    v['search_size'] = format_filesize(searcher.getSearchSize())
    
    #print v['search_info']
    
    return req.getTAL("web/admin/modules/settings.html", v, macro="view")

