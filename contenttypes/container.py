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
import logging
import codecs

from mediatumtal import tal
import core.config as config
from core import Node
from contenttypes.data import Data

from core.database.helpers import ContainerMixin
from core.translation import t, lang, getDefaultLanguage
from utils.utils import CustomItem
from core.transition.postgres import check_type_arg, check_type_arg_with_schema
from schema.schema import Metafield, SchemaMixin
try:
    import web.frontend.modules.modules as frontendmods
    frontend_modules = 1
except:
    frontend_modules = 0


logg = logging.getLogger(__name__)


SRC_PATTERN = re.compile('src="([^":/]*)"')

""" these are not TAL templates, but a much more simplified version. All that
    is replaced are images and links to ${next} """


def includetemplate(self, file, substitute):
    ret = ""
    if os.path.isfile(file):

        with codecs.open(file, "rb", encoding='utf8') as fi:
            s = unicode(fi.read())

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
    with open(file) as f:
        s = f.read().strip()
    if s:
        return 1
    else:
        return 0

""" directory class """


class Container(Data, ContainerMixin, SchemaMixin):

    """(Abstract) Base class for Nodes that contain other Container/Content nodes and are displayed in the navigation area.
    """

    # By default, a Container shows its children as a list.
    # Subclasses can set this to False if they want to display something else via show_node_big().
    show_list_view = True

    @classmethod
    def getTypeAlias(cls):
        return "directory"

    @classmethod
    def getOriginalTypeName(cls):
        return "directory"

    @classmethod
    def getCategoryName(cls):
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
                    try:
                        shortpath_file = f.retrieveFile().replace(basedir, "")
                    except IOError:
                        pass
                    else:
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
        content = u""
        link = u"node?id={}&amp;files=1".format(self.id)
        sidebar = u""
        pages = self.getStartpageDict()
        if self.get("system.sidebar") != "":
            for sb in self.get("system.sidebar").split(";"):
                if sb:
                    l, fn = sb.split(":")
                    if l == lang(req):
                        for f in self.getFiles():
                            if fn.endswith(f.getName()):
                                sidebar = includetemplate(self, f.retrieveFile(), {})
                                sidebar = replaceModules(self, req, sidebar).strip()
        if sidebar:
            sidebar = req.getTAL("contenttypes/container.html", {"content": sidebar}, macro="addcolumn")
        else:
            sidebar = u""

        if "item" in req.params:
            fpath = "{}html/{}".format(config.get("paths.datadir"),
                                       req.params.get("item"))
            if os.path.isfile(fpath):
                with codecs.open(fpath, "r", encoding='utf8') as c:
                    content = c.read()
                if sidebar:
                    return u'<div id="portal-column-one">{}</div>{}'.format(content,
                                                                           sidebar)
                return content

        spn = self.getStartpageFileNode(lang(req))
        if spn:
            long_path = spn.retrieveFile()
            if os.path.isfile(long_path) and fileIsNotEmpty(long_path):
                content = includetemplate(self, long_path, {'${next}': link})
                content = replaceModules(self, req, content)
            if content:
                if sidebar:
                    return u'<div id="portal-column-one">{}</div>{}'.format(content,
                                                                           sidebar)
                return content

        return u'{}{}'.format(content, sidebar)

    """ format node image with standard template """
    def show_node_image(self, language=None):
        return tal.getTAL("contenttypes/container.html", {"node": self}, macro="thumbnail", language=language)

    @classmethod
    def isContainer(cls):
        return 1

    def getSysFiles(self):
        return ["statistic", "image"]

    def getLabel(self, lang=getDefaultLanguage()):

        # try language-specific name first
        lang_value = self.get(u'{}.name'.format(lang))
        if lang_value:
            return self.get(u'{}.name'.format(lang))

        # always return the name if the requested lang matches the default language
        if self.name and lang == getDefaultLanguage():
            return self.name

        label = self.get(u"label")

        # still no label found, use name
        if not label:
            label = self.name

        return label

    """ list with technical attributes for type directory """
    def getTechnAttributes(self):
        return {}

    def getLogoPath(self):
        items = [f.base_name for f in self.files.filter_by(filetype=u"image")]
        if "system.logo" not in self.attributes.keys() and len(items) == 1:
            return items[0]
        else:
            logoname = self.get("system.logo")
            for item in items:
                if item == logoname:
                    return item
        return ""

    def metaFields(self, lang=None):
        metafields = []

        field = Metafield(u"nodename", attrs={
            "label": t(lang, "node name"),
            "type": u"text"
        })
        metafields.append(field)

        field = Metafield(u"style_full", attrs={
            "label": t(lang, "full view style"),
            "type": u"list",
            "valuelist": u"full_standard;full_text"
        })
        metafields.append(field)

        field = Metafield(u"style", attrs={
            "label": t(lang, "style"),
            "type": u"list",
            "valuelist": u"thumbnail;list;text",
        })
        metafields.append(field)
        return metafields

    def getEditMenuTabs(self):
        if self.type in ["collection", "collections"]:
            return "menulayout(content;startpages;view);menumetadata(metadata;logo;files;admin;searchmask;sortfiles);menusecurity(acls);menuoperation(search;subfolder;license)"

        elif self.type == "directory":
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
        self.set("system." + type, ";".join(unicode(i) for i in items))

    def event_files_changed(self):
        logg.debug("Postprocessing node %s", self.id)




# concrete Container classes

@check_type_arg_with_schema
class Directory(Container):

    @classmethod
    def treeiconclass(cls):
        return "directory"


@check_type_arg_with_schema
class Collection(Container):

    @classmethod
    def treeiconclass(cls):
        return "collection"

    def metaFields(self, lang=None):
        metafields = Container.metaFields(self, lang=lang)
        field = Metafield(u"style_hide_empty")

        field.set("label", t(lang, "hide empty directories"))
        field.set("type", u"check")
        metafields.append(field)
        return metafields


@check_type_arg_with_schema
class Collections(Container):
    
    def get_parent_container(self):
        pass

    def get_parent_collection(self):
        pass


@check_type_arg_with_schema
class Home(Container):
    
    def get_parent_container(self):
        pass

    def get_parent_collection(self):
        pass

