#!/usr/bin/python
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
sys.path += ["."]
import os
import time
import codecs

from core.init import basic_init
basic_init()

import core.tree as tree
import core.config
from core.stats import buildStat
from core.db import database

period = time.strftime("%Y-%m")
force = 0

if len(sys.argv) == 3 and sys.argv[1] == "--period":
    period = sys.argv[2]
else:
    p = period.split("-")
    if int(p[1]) - 1 == 0:
        p[0] = ustr(int(p[0]) - 1)
        p[1] = "12"
    else:
        p[1] = ustr("%2.2i" % (int(p[1]) - 1))

    period = "-".join(p)

period = "2014-12"

if len(sys.argv) == 2 and sys.argv[1] == "--force":
    print "force reprocess of log data"
    force = 1
    
LOG_FILENAME = core.config.get("logging.file.athana")

path = [LOG_FILENAME]
outpath = "%s%s.log" % (core.config.get("logging.save", os.path.dirname(LOG_FILENAME) + '/'), period)

if os.path.exists(outpath) and force == 0:
    print "file for period", period, "existing", outpath
    sys.exit()

for i in range(1, 21):
    path.append(LOG_FILENAME + "." + ustr(i))

d = []
for filename in path:
    with open(filename) as fin:
        for line in fin:
            if line.startswith(period):
                d.append(line)

d.sort()
with codecs.open(outpath, "w", encoding='utf8') as fout:
    for line in d:
        fout.write(line)
print "done for period", period, ", found", len(d), "lines."


if force == 1:  # force rebuildin stats
    print "rebuild stats for period", period
    db = database.getConnection()
    for id in db.runQuery("select id from node where type='collections' or type='collection'"):
        buildStat(tree.getNode(id[0]), period)
