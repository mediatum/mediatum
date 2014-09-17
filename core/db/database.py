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
from core.db import postgres

_db = None

logg = logging.getLogger("database")


class DatabaseException:

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "db exception: " + self.msg + "\n"


def getConnection():
    global _db
    if not _db:
        _db = postgres.PostgresSQLAConnector()
    return _db
