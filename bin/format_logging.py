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
import core.config

period = time.strftime("%Y-%m")

if len(sys.argv)==3 and sys.argv[1]=="--period":
    period = sys.argv[2]
else:
    p = period.split("-")
    if int(p[1])-1==0:
        p[0] = str(int(p[0])-1)
        p[1] = "12"
    else:
        p[1] = str("%2.2i" % (int(p[1]) - 1))
        
    period = "-".join(p)

path = [core.config.get("logging.file.everything")]
outpath = os.path.dirname(core.config.get("logging.file.everything"))+"/"+period+".log"

if os.path.exists(outpath):
    print "file for period", period, "existing"
    sys.exit()

for i in range(1, 21):
    path.append(core.config.get("logging.file.everything")+"."+str(i))

d = []
for filename in path:
    fin = open(filename)
    for line in fin:
        if line.startswith(period):
            d.append(line)
    fin.close()

d.sort()
fout = open(outpath, "w")
for line in d:
    fout.write(line)
fout.close()
print "done for period", period, ", found", len(d), "lines."

