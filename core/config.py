#!/usr/bin/python
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

import os
import sys
import codecs

#basedir = os.path.dirname(__file__).rsplit(os.sep, 1)[0]
# using abspath allows importing start.py or variants (wn 2014-11-20)
basedir = os.path.abspath(__file__).rsplit(os.sep, 2)[0]


# append our own fallback lib directory
sys.path.append(os.path.join(basedir, "external"))

settings = None
# append our own fallback lib directory
sys.path.append(os.path.join(basedir, "external"))


def get(key, default=None):
    return settings.get(key, default)


def getsubset(prefix):
    options = {}
    for k, v in settings.items():
        if k.startswith(prefix):
            k = k[len(prefix):]
            if k[0] == '.':
                k = k[1:]
            options[k] = v
    return options


def _read_ini_file(basedir, filename):
    lineno = 0
    params = {}
    with codecs.open(os.path.join(basedir, filename), "rb", encoding='utf8') as fi:
        module = ""
        for line in fi.readlines():
            lineno = lineno + 1
            # remove comments
            hashpos = line.find("#")
            if hashpos >= 0:
                line = line[0:hashpos]
            # remove whitespace
            line = line.strip()

            if line == "":
                pass  # skip empty line
            elif line[0] == '[':
                if line[-1] != ']':
                    raise "Syntax error in line " + ustr(lineno) + " of file " + filename + ":\n" + line
                module = line[1:-1]
            else:
                equals = line.find("=")
                if equals < 0:
                    raise "Syntax error in line " + ustr(lineno) + " of file " + filename + ":\n" + line
                key = module + "." + line[0:equals].strip()
                value = line[equals + 1:].strip()
                if(len(value) and value[0] == '\'' and value[-1] == '\''):
                    value = value[1:-1]
                params[key] = value

    for key, value in params.items():
        if key.startswith("paths") or key.endswith("file"):
            if not (value[0] == '/' or value[0] == '\\' or value[1] == ':'):
                value = os.path.join(basedir, value)
                params[key] = value
            else:
                pass  # path is absolute, don't bother

    return params


def mkDir(dir):
    try:
        os.mkdir(dir)
        print "Created directory", dir
    except:
        pass  # already exists


def initialize():
    global settings
    if settings:
        raise Exception("calling config.initialize() multiple times is not allowed!")
    if os.getenv("MEDIATUM_CONFIG"):
        ini_filename = os.getenv("MEDIATUM_CONFIG")
    else:
        ini_filename = "mediatum.cfg"
    settings = _read_ini_file(basedir, ini_filename)
    if not os.path.isdir(settings["paths.datadir"]):
        print "Couldn't find data directory", settings["paths.datadir"]
        sys.exit(1)

    for var in ["paths.datadir", "paths.searchstore", "paths.tempdir"]:
        if var not in settings:
            print "ERROR: config option", var, "not set"
            sys.exit(1)

    mkDir(os.path.join(settings["paths.datadir"], "search"))
    mkDir(os.path.join(settings["paths.datadir"], "html"))
    mkDir(os.path.join(settings["paths.datadir"], "log"))

#
# resolve given filename to correct path/file
#


def resolve_filename(filename):
    templatepath = settings.get("template.path")
    templatename = settings.get("template.name", None)
    if templatepath.startswith("/") or templatepath.startswith("\\"):
        pathlist = [templatepath]
    else:
        pathlist = [basedir, templatepath]
    if templatename:
        pathlist += [templatename]
    pathlist += [filename]

    newname = os.path.join(*pathlist)
    if os.path.exists(newname):
        return newname
    else:
        if filename.find("admin_") >= 0:
            return pathlist[0] + "/admin/template/" + filename
        elif filename.startswith("m_"):
            return pathlist[0] + "/metatypes/" + filename
    return filename
