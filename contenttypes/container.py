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
from warnings import warn

from mediatumtal import tal
import core.config as config
from core import Node, db
from core.webconfig import node_url
from contenttypes.data import Data

from core.database.helpers import ContainerMixin
from core.translation import t, lang, getDefaultLanguage
from utils.utils import CustomItem
from core.users import user_from_session as _user_from_session
from core.postgres import check_type_arg_with_schema
from schema.schema import Metafield, SchemaMixin


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
                    ret += 'src="/file/' + str(self.id) + '/' + imgname + '"'
                    lastend = match.end()
    return ret


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

    show_childcount = False

    item_file_pattern = re.compile("^\d+")

    # By default, a Container shows its children as a list.
    # Subclasses can set this to False if they want to display something else via show_node_big().
    show_list_view = True

    editor_menu = (
        "content",
        "metadata",
        { "menuoperation": (
            "acls",
            { "menueditall": (
                "editall",
                "moveall",
                "copyall",
                "deleteall",
                )},
            { "startpagesmenu": (
                "startpages",
                "logo",
                "searchmask",
                )},
            "admin",
            "subfolder",
            "sortfiles",
        )},
    )


    @classmethod
    def isContainer(cls):
        warn("use isinstance(node, Container) or issubclass(nodecls, Container)", DeprecationWarning)
        return 1

    @classmethod
    def get_sys_filetypes(cls):
        return [u"statistic", u"image"]

    @classmethod
    def get_default_edit_tab(cls):
        return "content"

    def getStartpageDict(self):
        d = {}
        descriptor = self.system_attrs.get('startpage_selector', '')
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
    def show_node_big(self, req, style_name=""):
        # style_name is ignored
        user = _user_from_session()
        content = u""
        link = node_url(self.id, files=1)
        pages = self.getStartpageDict()

        if "item" in req.params:
            fname = req.params.get("item")
            fname_allowed = False
            # accept only filenames which starts with a number and the number is a node_id and the current_user has
            # read access to this node, to avoid delivering of systemfiles like /etc/passwd
            # with e.g. 604993?item=../../../../../../../../../../etc/passwd
            node_id_list = self.item_file_pattern.findall(fname)
            if node_id_list:
                node_id = node_id_list[0]
                node = db.query(Node).get(node_id)
                fname_allowed = node and node.has_read_access(user=user)

            fpath = "{}html/{}".format(config.get("paths.datadir"),
                                       fname)
            if fname_allowed and os.path.isfile(fpath):
                with codecs.open(fpath, "r", encoding='utf8') as c:
                    content = c.read()
                return content

        spn = self.getStartpageFileNode(lang(req))
        if spn:
            long_path = spn.retrieveFile()
            if os.path.isfile(long_path) and fileIsNotEmpty(long_path):
                content = includetemplate(self, long_path, {'${next}': link})

        return content

    """ format node image with standard template """
    def show_node_image(self, language=None):
        return tal.getTAL("contenttypes/container.html", {"node": self}, macro="thumbnail", language=language)

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
        logo_name = self.system_attrs.get("logo")
        logo_base_names = [f.base_name for f in self.files.filter_by(filetype=u"image")]
        
        if logo_name:
            found_logos = [f for f in logo_base_names if f == logo_name]
            if found_logos:
                return found_logos[0]
        # XXX: do we really want this legacy behaviour of using the only image as collection logo?
        elif len(logo_base_names) == 1:
            return logo_base_names[0]

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

    def get_container(self):
        return self

    def childcount(self):
        return self.content_children_count_for_all_subcontainers


# concrete Container classes

@check_type_arg_with_schema
class Directory(Container):

    show_childcount = True
    
    @classmethod
    def treeiconclass(cls):
        return "directory"

    def get_directory(self):
        return self


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

    def get_collection(self):
        return self

    def childcount(self):
        if self.children.first() is None:
            return 0
        
        return 1


@check_type_arg_with_schema
class Collections(Container):

    # XXX: as in other places, we assume that the Collections root is public.
    cache_duration = 600

    def get_collection(self):
        return self

    def childcount(self):
        if self.children.first() is None:
            return 0
        
        return 1


@check_type_arg_with_schema
class Home(Container):
    pass

