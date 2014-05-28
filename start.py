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
import time
import core
import core.webconfig
import core.config as config
import subprocess
import urllib2
from utils.utils import formatException

webserverprocess = None
restarted = False
restarttime = config.get("config.restart_time", "00:00:00").split(":")

if config.get("config.searcher", "").startswith("fts"):
    import core.search.ftsquery
    from core.search.router import router
    #for searcher in router.schemas.values():
        #core.search.ftsquery.startThread(searcher)
else:
    import core.search.query
    core.search.query.startThread()


def startWebServer():
    global webserverprocess
    webserverprocess = subprocess.Popen("python startathana.py", shell=True)
    time.sleep(5)
    fileHandle = urllib2.urlopen("http://" + config.get("host.name", ""))
    data = fileHandle.read()
    fileHandle.close()

if config.get("config.restart_time", "00:00:00")=="00:00:00":

    import core.schedules
    try:
        core.schedules.startThread()
    except:
        msg = "Error starting scheduler thread: %s %s" % (str(sys.exc_info()[0]), str(sys.exc_info()[1]))
        core.schedules.OUT(msg, logger='backend', print_stdout=True, level='error')

    # no internal restart process
    core.webconfig.startWebServer()


else:
    # use internal restart process
    while (1):
        time.sleep(1)
        localtime = time.localtime()
        if (localtime.tm_hour==int(restarttime[0]) and localtime.tm_min==int(restarttime[1])):
            if (not restarted):
                try:
                    if webserverprocess:
                        print "Killing server..."
                        try:
                            os.popen("kill -9 " + str(webserverprocess.pid))
                        except:
                            print "Killed server!"
                            print formatException()
                        time.sleep(2)
                    print "Restarting webserver..."
                    startWebServer()
                    restarttime = [str(time.localtime().tm_hour), str(time.localtime().tm_min+1)]
                    restarted = True
                except:
                    print "Could not restart webserver... Retrying!"
                    print formatException()
            else:
                restarted = False
