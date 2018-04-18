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
from core import init, db, Node
from core import config
from contenttypes import Collections, Collection
import os, re, argparse, tempfile
from itertools import imap, ifilter, repeat
import operator

"""
if parameter is given it will be used as period, format: %Y-%m
if not given, current month will be used as period
"""

def main():
    """
    create or append a logfile with name yyyy-mm.log as an excerpt of mediatum.log
    of lines beginning with period and containing the string 'INFO' and containing one of the strings:
    'GET', 'POST' or 'HEAD are excerpted
    usage: find /home/congkhacdung/logrotated/ -type f -iname 'mediatum.*.log' | sort | xargs cat | python bin/stats.py --skip-ip 127.0.0.1 --skip-ip 129.187.87.37 2018 2
    """
    parser = argparse.ArgumentParser(description='Extract info needed for statistics.')
    parser.add_argument('--skip-ip', dest='skip_ip', action='append', default=[], help='ip to skip')
    parser.add_argument('year', type=int, help='year')
    parser.add_argument('month', type=int, help='month')
    args = parser.parse_args()
    period = "{:4}-{:0>2}".format(args.year, args.month)
    skip_ip = args.skip_ip

    outdir = os.path.join(config.get("logging.save", config.get("logging.path", "/tmp")))
    match = re.compile('^({period}.{{17}}).*(INFO).{{2}}(.*(?:GET|POST|HEAD).*)'.format(period=period)).match
    lines = sys.stdin
    lines = imap(match, lines)
    lines = ifilter(None, lines)
    lines = imap(operator.methodcaller('groups'), lines)

    skip_ip_pattern = map("([^0-9.]{}[^0-9.])".format, skip_ip)
    skip_ip_pattern = '|'.join(skip_ip_pattern)
    match = re.compile(skip_ip_pattern).match
    lines = ifilter(lambda g: not match(g[2]), lines)
    lines = imap(operator.concat, lines, repeat(("\n",)))
    lines = imap("".join,lines)

    with tempfile.NamedTemporaryFile(dir=outdir) as tmpfile:
        tmpfile.writelines(lines)
        tmpfile.close()
        init.full_init()
        buildStatAll([], period, tmpfile.name)

if __name__ == '__main__':
    main()
