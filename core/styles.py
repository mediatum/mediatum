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

import codecs
import logging
from mediatumtal import tal
import os
import core.config as config
from utils.utils import splitpath


contentstyles = {}


logg = logging.getLogger(__name__)


class Theme:

    def __init__(self, name, path="web/themes/mediatum/", type="intern"):
        self.name = name
        self.path = path
        self.type = type

    def update(self, name, path, type):
        self.name = name
        self.path = path
        self.type = type

    def getImagePath(self):
        return self.path + "/img/"

    def getName(self):
        return self.name

    def getTemplate(self, filename):
        if os.path.exists(os.path.join(config.basedir, self.path + filename)):
            return self.path + filename
        else:
            return "web/themes/mediatum/" + filename

theme = Theme("default", "web/themes/mediatum/", "default")


class ContentStyle:

    def __init__(self, type="type", contenttype="all", name="name", label="label",
                 icon="icon", template="template", default="", description=""):
        self.type = type
        self.contenttype = contenttype
        self.name = name
        self.label = label
        self.icon = icon
        self.template = template
        self.default = default
        self.description = description

    def getID(self):
        if self.contenttype != "all" and self.contenttype != "":
            return "%s_%s" % (self.contenttype, self.name)
        return self.name

    def getType(self):
        return self.type

    def getContentType(self):
        return self.contenttype

    def getName(self):
        return self.name

    def getLabel(self):
        return self.label

    def getIcon(self):
        return self.icon

    def getTemplate(self):
        return self.template

    def getThemePath(self):
        return theme.path

    def getDescription(self):
        return self.description

    def isDefaultStyle(self):
        if ustr(self.default) == "true":
            return 1
        return 0

    # build
    def renderTemplate(self, req, params={}):
        try:
            return tal.getTAL(self.getTemplate(), params, request=req)
        except Exception as e:
            logg.exception("exception in template")
            return "error in template"


def readStyleConfig(filename):
    path, file = splitpath(filename)
    attrs = {"type": "", "contenttype": "", "name": "", "label": "", "icon": "",
             "template": path.replace(config.basedir, "") + "/", "description": "", "default": ""}

    with codecs.open(filename, "rb", encoding='utf8') as fi:
        for line in fi:
            if line.find("#") < 0:
                line = line.split("=")
                if line[0].strip() in attrs.keys():
                    attrs[line[0].strip()] += line[1].replace("\r", "").replace("\n", "").strip()

    return ContentStyle(attrs["type"], attrs["contenttype"], attrs["name"], attrs["label"],
                        attrs["icon"], attrs["template"], attrs["default"], attrs["description"])


def getContentStyles(type, name="", contenttype=""):
    name = name.split(";")[0]
    global contentstyles

    if len(contentstyles) == 0:
        styles = {}
        # load standard themes
        for root, dirs, files in os.walk(os.path.join(config.basedir, 'web/frontend/styles')):
            for n in [f for f in files if f.endswith(".cfg")]:
                c = readStyleConfig(root + "/" + n)
                styles[c.getID()] = c

        # test for external styles by plugin (default for user types) and theme styles of plugin styles
        for k, v in config.getsubset("plugins").items():
            path, module = splitpath(v)

            if os.path.exists(os.path.join(config.basedir, v)):
                for root, dirs, files in os.walk(os.path.join(config.basedir, v)):
                    for n in [f for f in files if f.endswith(".cfg")]:
                        c = readStyleConfig(root + "/" + n)
                        styles[c.getID()] = c
                    break

            if os.path.exists(os.path.join(config.basedir, v + "themes/" + theme.getName() + "/styles")):
                for root, dirs, files in os.walk(os.path.join(config.basedir, v + "themes/" + theme.getName() + "/styles")):
                    for n in [f for f in files if f.endswith(".cfg")]:
                        c = readStyleConfig(root + "/" + n)
                        styles[c.getID()] = c

        contentstyles = styles

    if contenttype != "":
        ret = filter(lambda x: x.getContentType() == contenttype, contentstyles.values())
        if len(ret) > 0:
            if name != "":
                return filter(lambda x: x.getName() == name, ret)
            else:
                return ret
        else:
            return []

    if name != "":
        if name in contentstyles.keys():
            return contentstyles[name]
        else:
            return contentstyles.values()[0]
    return filter(lambda x: x.getType() == type, contentstyles.values())
