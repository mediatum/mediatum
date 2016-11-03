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


from core.stats import buildStatAll
from core import init, db, Node, config
from contenttypes import Collections, Collection
import os

"""
if parameter is given it will be used as period, format: %Y-%m
if not given, current month will be used as period
"""

def create_logfile(period):
    """
    create a logfile with name yyyy-mm.log as an excerpt of mediatum.log
    on line beginning with period and containing the string 'INFO' and containing one of the strings:
    'GET', 'POST' or 'HEAD are excerpted
    :param period: format: yyyy-mm
    :return: none
    """
    outpath = "%s.log" % os.path.join(config.get("logging.save", config.get("logging.path", "/tmp")), period)
    MEDIATUM_LOG = os.path.join(config.get("logging.path"), "mediatum.log")

    fin = open(MEDIATUM_LOG)
    fout = open(outpath, "w")
    # do a binary search for the period in mediatum.log
    fin.seek(0, os.SEEK_SET)
    fpos0 = fin.tell()
    fin.seek(0, os.SEEK_END)
    fpos1 = fin.tell()
    y = period[0:5]
    while fpos1 - fpos0 > 4096:
        fpos = (fpos1 + fpos0) / 2
        fin.seek(fpos, os.SEEK_SET)
        line = fin.readline()
        line = fin.readline()
        while line and not line.startswith(y):
            line = fin.readline()
        if (line >= period):
            fpos1 = fpos
        else:
            fpos0 = fpos

    fin.seek(fpos0,os.SEEK_SET)
    line = fin.readline()

    period_len = len(period)
    for line in fin.readlines():
        if not line.startswith(y):
            continue
        if line[0:period_len] < period:
            continue
        if line[0:period_len] > period:
            break
        pos = line.find("INFO")
        if pos < 0:
            continue
        if line[pos:].find('"GET') < 0 and line[pos:].find('"POST') < 0 and line[pos:].find('"HEAD') < 0:
            continue
        fout.write(line[0:24] + line[pos:pos+5] + line[pos+6:])

    fin.close()
    fout.close()


init.full_init()
args = sys.argv
period = time.strftime("%Y-%m")
fname = None
create_new_logfile = True

if len(args) >= 2 and args[1] == "-nolog":
    create_new_logfile = False
    args = args[1:]

if len(args) == 2:  # period given
    period = args[1]

if len(args) == 3:  # period and filename given
    period = args[1]
    fname = args[2]

if create_new_logfile:
    create_logfile(period)

buildStatAll([], period, fname)
