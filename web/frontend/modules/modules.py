"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <seiferta@in.tum.de>

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
import os
import sys
import traceback

import core.config as config
from core.translation import addLabels

# prototype of module to be used in frontend


logg = logging.getLogger(__name__)


class FrontendModule:

    def __init__(self):
        addLabels(self.addModLabels())

    def getName(self):
        return "prototype module"

    def getId(self):
        return ""

    def getContent(self, req, path="", no=0):
        pass

    def hasParams(self):
        return 0

    def getParameterInfo(self):
        pass

    def addModLabels(self):
        return {}


def getContent(req):  # deliver content of act
    path = req.path.split("/")
    modname = path[1]
    if modname == "init":  # maintenance of frontend modules
        if path[2] == "editor":
            getMaintenancePopup(req)
            return
        if path[2] == "moduleform":
            if len(path) == 4 and path[3] != "":
                mod = getFrontendModules(path[3].split(".")[-1])
                try:
                    req.write(mod().getModuleForm(req))
                except:
                    logg.exception("exception in getContent, ignoring")
                return
            getDefaultModuleForm(req)  # default content of form
            return
    mod = getFrontendModules(modname)
    if mod:
        mod().getContent(req)


def getFrontendModules(modname=""):
    mods = {}
    for root, dirs, files in os.walk(config.basedir + "/web/frontend/modules/"):
        for name in dirs:
            if name.lower() in ['cvs']:  # exclude sys dir
                continue
            try:
                m = __import__("web.frontend.modules." + name)
                m = eval("web.frontend.modules." + name)
            except:
                logg.exception("couldn't load frontend module %s", name)
                
            if modname == name:
                return getattr(m, name)
            mods[name] = getattr(m, name)
    if modname == "":
        return mods
    else:
        return None


def getEditorModules():
    ret = []
    mods = getFrontendModules()
    for k in mods:
        try:
            if mods[k]().hasParams():
                ret.append(mods[k])
        except:
            logg.exception("exception in getEditorModules")
            
    return ret


def getMaintenancePopup(req):
    req.writeTAL("web/frontend/modules/editor.html", {'mods': getEditorModules()}, macro="editor_popup")


def getDefaultModuleForm(req):
    req.writeTAL("web/frontend/modules/editor.html", {}, macro="editor_default")
