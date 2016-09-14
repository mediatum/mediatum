"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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
sys.path += ["../", "."]
import time

from core.init import basic_init
basic_init(prefer_config_filename="stats.log")


from core.stats import buildStat
from core.db import database

"""
if parameter is given it will be used as period, format: %Y-%m
if not given, current month will be used as period
"""

db = database.getConnection()
args = sys.argv
period = time.strftime("%Y-%m")
fname = None

if len(args) == 2:  # period given
    period = args[1]

if len(args) == 3:  # period and filename given
    period = args[1]
    fname = args[2]

for id in db.runQuery("select id from node where type='collections' or type='collection'"):
    buildStat(tree.getNode(id[0]), period, fname)
