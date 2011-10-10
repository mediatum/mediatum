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
import core.athana as athana
import core.config as config
import os

from utils.utils import format_filesize, get_filesize
from utils.log import dlogfiles
from web.admin.adminutils import Overview,getAdminStdVars

def getInformation():
    return{"version":"1.0"}

class LogFile:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.size = format_filesize(get_filesize(path))

    def getName(self):
        return self.name
    def getPath(self):
        return self.path
    def getSize(self):
        return self.size

def getLogFiles():
    f = []
    logtypes = dlogfiles.keys()
    logtypes.sort()
    for name in logtypes:
        f += [LogFile("admin_log_"+name, dlogfiles[name]['filename'])]
    return f

filelist = getLogFiles()

def validate(req, op):
    return view(req, op)

def view(req, op):
    global filelist
    logfile = None
    name = ""

    pages = Overview(req, filelist)
    v = getAdminStdVars(req)
    v["filelist"] = filelist
    v["pages"] = pages
    text = req.getTAL("web/admin/modules/logfile.html", v, macro="view")

    # refresh part
    if "name" in req.params.keys():
        name = req.params.get("name","")

    # load file part
    for key in req.params.keys():
        if key.startswith("view_"):
            name = key[5:-2]

    for file in filelist:
        if file.getName()==name:
            logfile = file

    # return form with file-content
    if logfile!=None:
        text += req.getTAL("web/admin/modules/logfile.html", {"logfile":logfile, "content":getFileContent(logfile.getPath())}, macro="detail")
    return text

def getFileContent(path):
    try:
        fileHandle = open(path)
        fileList = fileHandle.readlines()
        _text = ""
        for fileLine in fileList:
            _text += fileLine
        fileHandle.close()
        return _text
    except:
        return ""