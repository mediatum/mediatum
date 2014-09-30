#!/bin/sh
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

from version import mediatum_version
from os import system


def build_package():
    global files
    name = "mediatum-%s" % mediatum_version
    print "creating %s.tar.gz" % name

    system("rm -f %(name)s" % locals())
    system("rm -f %(name)s.tar" % locals())
    system("rm -f %(name)s.tar.gz" % locals())
    system("ln -s . %(name)s" % locals())

    command = "tar -chf %(name)s.tar " % locals()
    for file in files:
        command += name + file + " "
    system(command)
    system("gzip -9 %(name)s.tar" % locals())
    system("rm -f %(name)s" % locals())

files = [
    "/COPYING",
    "/version.py"
]

build_package()
