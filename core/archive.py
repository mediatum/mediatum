"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2009 Matthias Kramm <kramm@in.tum.de>

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
import thread
import time
import logging
import core.config as config
from utils.utils import splitpath, intersection, union
from utils.date import parse_date, now, format_date


logg = logging.getLogger(__name__)


class Archive:

    def __init__(self):
        self.lock = thread.allocate_lock()

    def acquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()

    def getLockState(self):
        return self.lock

    def actionArchive(self, nodes):
        None

    def getArchivedFile(self, node):
        None

    def getArchivedFileStream(self, filename):
        None

    def deleteFromArchive(self, filename):
        None

    def writelog(self, message="", level="info"):
        logg.log(level, message)

    def info(self):
        self.version = "0.1"
        return "no description of archive manager found"

    def stat(self, attribute=""):
        stat = {}
        stat['name'] = ustr(self)
        stat['used'] = db.getNodeIdByAttribute("archive_type", ustr(self))
        stat['state1'] = len(intersection([stat['used'], db.getNodeIdByAttribute("archive_state", "1")]))
        stat['state2'] = len(intersection([stat['used'], db.getNodeIdByAttribute("archive_state", "3")]))
        stat['state3'] = len(intersection([stat['used'], db.getNodeIdByAttribute("archive_state", "3")]))
        stat['used'] = len(stat['used'])

        if attribute == "":
            return stat
        elif attribute in stat.keys():
            return stat[attribute]


class ArchiveManager:

    def __init__(self):
        self.manager = {}
        if config.get("archive.activate", "").lower() == "true":
            logg.info("Initializing archive manager")
            for paths in config.get("archive.class").split(";"):
                path, manager = splitpath(paths)
                self.manager[manager] = paths

        logg.debug("archivemanager init done %s", len(self.manager))

    def getManager(self, name=""):
        if name == "":
            return self.manager

        if name in self.manager.keys():
            path, manager = splitpath(self.manager[name])
            if path and path not in sys.path:
                sys.path += [path]
            return __import__(manager).__dict__[manager]()
        return None
