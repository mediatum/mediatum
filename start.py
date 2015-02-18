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
import codecs

from core import config, webconfig, init
from core import athana

init.full_init()


logg = logging.getLogger(__name__)

### stackdump
import os
import threading
import traceback
try:
    import IPython.core.ultratb as ultratb
except:
    ultratb = None

if ultratb is not None:
    def dumpstacks(signal, frame):
        filepath = os.path.join(config.get("paths.tempdir", "/tmp"), "mediatum_threadstatus")
        id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
        full = ["-" * 80]
        tb_formatter = ultratb.ListTB(color_scheme="Linux")
        for thread_id, stack in sys._current_frames().items():
            thread_name = id2name.get(thread_id, "")
            if not "Main" in thread_name:
                stacktrace = traceback.extract_stack(stack)
                stb = tb_formatter.structured_traceback(Exception, Exception(), stacktrace)[8:-1]
                if stb:
                    formatted_trace = tb_formatter.stb2text(stb).strip()
                    with codecs.open("{}.{}".format(filepath, thread_id), "w", encoding='utf8') as wf:
                        wf.write("\n{}".format(formatted_trace))
                    if len(stb) > 4:
                        short_stb = stb[:2] + ["..."] + stb[-2:]
                    else:
                        short_stb = stb
                    formatted_trace_short = tb_formatter.stb2text(short_stb).strip()
                    full.append("# Thread: %s(%d)" % (thread_name, thread_id))
                    full.append(formatted_trace_short)
                    full.append("-" * 80)


        with codecs.open(filepath, "wf", encoding='utf8') as wf:
            wf.write("\n".join(full))

    import signal
    signal.signal(signal.SIGQUIT, dumpstacks)

### init all web components
webconfig.initContexts()

### scheduler thread
import core.schedules
try:
    core.schedules.startThread()
except:
    logg.exception("Error starting scheduler thread")

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
