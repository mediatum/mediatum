#! /usr/bin/env nix-shell
#! nix-shell -i python

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

from core import config, webconfig, init
from core import athana

init.full_init()

### init all web components
webconfig.initContexts()

### scheduler thread
import core.schedules
try:
    core.schedules.startThread()
except:
    msg = "Error starting scheduler thread: %s %s" % (str(sys.exc_info()[0]), str(sys.exc_info()[1]))
    core.schedules.OUT(msg, logger='backend', print_stdout=True, level='error')

### full text search thread
if config.get("config.searcher", "").startswith("fts"):
    import core.search.ftsquery
    core.search.ftsquery.startThread()
else:
    import core.search.query
    core.search.query.startThread()


### start main web server, Z.39.50 and FTP, if configured
if config.get('z3950.activate', '').lower() == 'true':
    z3950port = int(config.get("z3950.port", "2021"))
else:
    z3950port = None
athana.setThreads(int(config.get("host.threads", "8")))
athana.run(int(config.get("host.port", "8081")), z3950port)
