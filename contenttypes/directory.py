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
import re
import os

from mediatumtal import tal
import core.tree as tree
import core.config as config
from . import default

from core.translation import t, lang
from utils.utils import CustomItem
try:
    import web.frontend.modules.modules as frontendmods
    frontend_modules = 1
except:
    frontend_modules = 0


SRC_PATTERN = re.compile('src="([^":/]*)"')

""" these are not TAL templates, but a much more simplified version. All that
    is replaced are images and links to ${next} """


def includetemplate(self, file, substitute):
    ret = ""
    if os.path.isfile(file):

        fi = open(file, "rb")
        s = str(fi.read())

        for string, replacement in substitute.items():
            s = s.replace(string, replacement)

        lastend = 0
        scanner = SRC_PATTERN.scanner(s)
        while True:
            match = scanner.search()
            if match is None:
                ret += s[lastend:]
                break
            else:
                ret += s[lastend:match.start()]
                imgname = match.group(1)
                ret += 'src="/file/' + self.id + '/' + imgname + '"'
                lastend = match.end()
        fi.close()
    return ret


def replaceModules(self, req, input):
    if frontend_modules:
        frontend_mods = frontendmods.getFrontendModules()

        def getModString(m):
            for k in frontend_mods:
                if m.group(0).startswith('{frontend/' + k + '/'):
                    return m.group(0), frontend_mods[k]().getContent(req, path=m.group(0)[1:-1].replace('frontend/' + k + '/', ""))
            return "", ""

        while True:
            m = re.compile('{frontend/.[^{]*}').search(input)
            if m:
                mod_str, mod_repl = getModString(m)
                input = input.replace(mod_str, mod_repl)
            else:
                break
    return input


def fileIsNotEmpty(file):
    f = open(file)
    s = f.read().strip()
    f.close()
    if s:
        return 1
    else:
        return 0

""" directory class """


class Directory(default.Default):

    def getTypeAlias(self):
        return "directory"

    def getOriginalTypeName(self):
        return "directory"

    def getCategoryName(self):
        return "container"

    def getStartpageDict(self):
        d = {}
        descriptor = self.get('startpage.selector')
        for x in descriptor.split(';'):
            if x:
                key, value = x.split(':')
                d[key] = value

        return d

    def getStartpageFileNode(self, language, verbose=False):
        res = None
        basedir = config.get("paths.datadir")
        d = self.getStartpageDict()

        if d and (language in d.keys()):
            shortpath_dict = d[language]
            if shortpath_dict:
                for f in self.getFiles():
                    shortpath_file = f.retrieveFile().replace(basedir, "")
                    if shortpath_dict == shortpath_file:
                        res = f
        if not d:
            for f in self.getFiles():
                shortpath_file = f.retrieveFile().replace(basedir, "")
                if f.getType() == 'content' and f.mimetype == 'text/html':
                    res = f
        return res

    """ format big view with standard template """
    def show_node_big(self, req, template="", macro=""):
        content = ""
        link = "node?id=" + self.id + "&amp;files=1"
        sidebar = ""
        pages = self.getStartpageDict()
        if self.get("system.sidebar") != "":
            for sb in self.get("system.sidebar").split(";"):
                if sb != "":
                    l, fn = sb.split(":")
                    if l == lang(req):
                        for f in self.getFiles():
                            if fn.endswith(f.getName()):
                                sidebar = includetemplate(self, f.retrieveFile(), {})
                                sidebar = replaceModules(self, req, sidebar).strip()
        if sidebar != "":
            sidebar = req.getTAL("contenttypes/directory.html", {"content": sidebar}, macro="addcolumn")
        else:
            sidebar = ""

        if "item" in req.params:
            fpath = config.get("paths.datadir") + "html/" + req.params.get("item")
            if os.path.isfile(fpath):
                c = open(fpath, "r")
                content = c.read()
                c.close()
                if sidebar != "":
                    return '<div id="portal-column-one">' + content + '</div>' + sidebar
                return content

        spn = self.getStartpageFileNode(lang(req))
        if spn:
            long_path = spn.retrieveFile()
            if os.path.isfile(long_path) and fileIsNotEmpty(long_path):
                content = includetemplate(self, long_path, {'${next}': link})
                content = replaceModules(self, req, content)
            if content:
                if sidebar != "":
                    return '<div id="portal-column-one">' + content + '</div>' + sidebar
                return content

        return content + sidebar

    """ format node image with standard template """
    def show_node_image(self, language=None):
        return tal.getTAL("contenttypes/directory.html", {"node": self}, macro="thumbnail", language=language)

    def isContainer(self):
        return 1

    def getSysFiles(self):
        return ["statistic", "image"]

    def getPossibleChildContainers(self):
        if self.type.startswith("directory"):
            return ["directory"]
        elif self.type in ["collection", "collections"]:
            return ["directory", "collection"]
        else:
            return []

    def getLabel(self, lang=None):
        if lang and self.get(str(lang) + '.name') != "":
            return self.get(str(lang) + '.name')
        label = self.get("label")
        if not label:
            label = self.getName()
        return label

    """ list with technical attributes for type directory """
    def getTechnAttributes(self):
        return {}

    def getLogoPath(self):
        items = []
        for file in self.getFiles():
            if file.getType() == 'image':
                items.append(file.getName())

        if "system.logo" not in self.attributes.keys() and len(items) == 1:
            return items[0]
        else:
            logoname = self.get("system.logo")
            for item in items:
                if item == logoname:
                    return item
        return ""

    def metaFields(self, lang=None):
        ret = list()

        field = tree.Node("nodename", "metafield")
        field.set("label", t(lang, "node name"))
        field.set("type", "text")
        ret.append(field)

        field = tree.Node("style_full", "metafield")
        field.set("label", t(lang, "full view style"))
        field.set("type", "list")
        field.set("valuelist", "full_standard;full_text")
        ret.append(field)

        field = tree.Node("style", "metafield")
        field.set("label", t(lang, "style"))
        field.set("type", "list")
        field.set("valuelist", "thumbnail;list;text")
        ret.append(field)

        if self.type.startswith(("collection", "directory")):
            # special fields for collections
            field = tree.Node("repec.code", "metafield")
            field.set("label", t(lang, "RePEc archive code"))
            field.set("language", "no")
            field.set("type", "text")
            ret.append(field)

            field = tree.Node("repec.provider", "metafield")
            field.set("label", t(lang, "RePEc provider"))
            field.set("language", "no")
            field.set("type", "text")
            ret.append(field)

            field = tree.Node("style_hide_empty", "metafield")
            field.set("label", t(lang, "hide empty directories"))
            field.set("type", "check")
            ret.append(field)

        elif self.type.startswith("directory"):
            # special fields for directories
            pass

        return ret

    def getEditMenuTabs(self):
        if self.getContentType() in ["collection", "collections"]:
            return "menulayout(content;startpages;view);menumetadata(metadata;logo;files;admin;searchmask;sortfiles);menusecurity(acls);menuoperation(search;subfolder;license)"

        elif self.getContentType() == "directory":
            return "menulayout(content;startpages;view);menumetadata(metadata;files;admin);menusecurity(acls);menuoperation(search;subfolder;license)"

        else:
            return "menulayout(content;startpages;view);menusecurity(acls);menuoperation(search;subfolder;license)"

    def getDefaultEditTab(self):
        return "content"

    def getCustomItems(self, type=""):
        ret = []
        items = {}
        items[type] = self.get("system." + type).split(";")

        for item in items[type]:
            if item != "":
                item = item.split("|")
                if len(item) == 4:
                    ci = CustomItem(item[0], item[1], item[2], item[3])
                ret.append(ci)
        return ret

    def setCustomItems(self, type, items):
        self.set("system." + type, ";".join(str(i) for i in items))

    def event_files_changed(self):
        print "Postprocessing node", self.id

    def treeiconclass(self):
        if 'collection' in self.type:
            return "collection"
        else:
            return "directory"
