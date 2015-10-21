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
import logging
from collections import OrderedDict
import time
from warnings import warn

import core.config as config

from schema.schema import getMetadataType
from utils.utils import getCollection, getDirectory, Link, isCollection, isDirectory, isParentOf
from core.translation import lang, t
from core.metatype import Context
from core.styles import theme
from core import db, User, users
from contenttypes import Collections
from sqlalchemy.orm.exc import NoResultFound
from core import Node
from core.systemtypes import Searchmasks, Root
from contenttypes import Directory, Container
from core.users import get_guest_user

q = db.query
logg = logging.getLogger(__name__)


class Portlet:

    def __init__(self):
        self.folded = 0
        self.name = "common"
        self.user = get_guest_user()

    def isFolded(self):
        return self.folded

    def close(self):
        if self.canClose():
            self.folded = 1

    def open(self):
        if self.canOpen():
            self.folded = 0

    def canClose(self):
        return 1

    def canOpen(self):
        return 1

    def feedback(self, req):
        self.user = users.user_from_session(req.session)
        r = req.params.get(self.name, "")
        if r == "unfold":
            self.open()
        elif r == "fold":
            self.close()
        self.language = lang(req)

    def getFoldUnfoldLink(self):
        if self.folded:
            return "node?" + self.name + "=unfold"
        else:
            return "node?" + self.name + "=fold"


def getSearchMask(collection):
    if collection.get("searchtype") == "none":
        return None
    mask = None
    n = collection
    if collection.get("searchtype") == "parent":
        while len(n.getParents()):
            if n.get("searchtype") == "own":
                break
            n = n.getParents()[0]
    if n.get("searchtype") == "own":
        searchmasks = q(Searchmasks).one()
        mask = searchmasks.children.filter_by(name=n.get("searchmaskname")).scalar()
    return mask


class Searchlet(Portlet):

    def __init__(self, collection):
        Portlet.__init__(self)
        self.name = "searchlet"
        self.extended = 0
        self.folded = 0
        self.collection = collection
        self.searchmask = getSearchMask(collection)

        self.values = [None] + [""] * 10
        self.req = None
        self.initialize()

    def insideCollection(self):
        return self.collection and not isinstance(self.collection, Collections)

    def initialize(self):
        types = {}
        firsttype = None

        # get searchfields for collection
        self.searchfields = OrderedDict()

        if self.searchmask:
            for field in self.searchmask.getChildren().sort_by_orderpos():
                self.searchfields[field.id] = field.name
        self.names = [None] * 11

    def feedback(self, req):
        Portlet.feedback(self, req)
        self.req = req
        extendedfields = range(1, 4)

        if "searchmode" in req.params:
            if req.params["searchmode"] == "simple":
                self.extended = 0
            if req.params["searchmode"] == "extendedsuper":
                self.extended = 2
                extendedfields = range(1, 11)
            if req.params["searchmode"] == "extended":
                self.extended = 1

        for i in extendedfields:
            if "field" + ustr(i) in req.params:
                newname = req.params.get("field" + ustr(i), "full")
                if newname != self.names[i]:
                    self.values[i] = ""
                self.names[i] = newname

            name = self.names[i]
            if name == "full" or not name:
                f = None
            else:
                node = q(Node).get(name)
                if node is not None:
                    f = node.getFirstField()
                else:
                    f = None

            if "query" + ustr(i) in req.params or "query" + ustr(i) + "-from" in req.params:
                if f and f.getFieldtype() == "date":
                    self.values[i] = req.params.get("query" + ustr(i) + "-from", "") + ";" + req.params.get("query" + ustr(i) + "-to", "")
                else:
                    self.values[i] = req.params.get("query" + ustr(i), "")

        if "query" in req.params:
            self.values[0] = req.params["query"]

    def hasExtendedSearch(self):
        return self.searchmask is not None

    def setExtended(self, value):  # value 0:simple, 1:extended, 2:extendedsuper
        self.extended = value

    def isSimple(self):
        return self.extended == 0 or self.searchmask is None

    def isExtended(self):
        return self.extended > 0 and self.searchmask is not None

    def isExtendedNormal(self):
        return self.extended == 1 and self.searchmask is not None

    def isExtendedSuper(self):
        return self.extended == 2 and self.searchmask is not None

    def query(self):
        return self.values[0]

    def searchLinkSimple(self):
        return "node?searchmode=simple&submittype=change"

    def searchLinkExtended(self):
        return "node?searchmode=extended&submittype=change"

    def searchLinkExtendedSuper(self):
        return "node?searchmode=extendedsuper&submittype=change"

    def searchActiveLeft(self):
        return not self.extended

    def searchActiveRight(self):
        return self.extended

    def getSearchFields(self):
        return self.searchfields

    def getSearchField(self, i, width=174):
        try:
            f = None
            if self.names[i] and self.names[i] != "full":
                f = q(Node).get(self.names[i]).getFirstField()
            g = None
            if f is None:  # All Metadata
                # quick&dirty
                f = g = getMetadataType("text")
            return f.getSearchHTML(Context(g, value=self.values[i], width=width, name="query" + unicode(i),
                                           language=lang(self.req), collection=self.collection,
                                           user=users.getUserFromRequest(self.req), ip=self.req.ip))
        except:
            # workaround for unknown error
            logg.exception("exception in getSearchField, return empty string")
            return ""


class NavTreeEntry(object):

    def __init__(self, col, node, indent, small=0, hide_empty=0, lang=None):
        self.col = col
        assert isinstance(node, Container)
        self.node = node
        self.id = node.id
        self.orderpos = node.orderpos
        self.indent = indent
        self.defaultopen = indent == 0
        self.hassubdir = 0
        self.folded = 1
        self.active = 0
        self.small = small
        self.count = -1
        self.hide_empty = hide_empty
        self.lang = lang
        self.orderpos = 0
        if self.node.container_children.first() is not None:
            self.hassubdir = 1
            self.folded = 1

    def isRoot(self):
        return isinstance(self.node, Collections)

    def getFoldLink(self):
        return u"/?cfold={}&dir={}&id={}".format(self.node.id,
                                                 self.node.id,
                                                 self.node.id)

    def getUnfoldLink(self):
        return u"/?cunfold={}&dir={}&id={}".format(self.node.id,
                                                   self.node.id,
                                                   self.node.id)

    def getLink(self):
        if self.folded:
            return self.getUnfoldLink()
        return self.getFoldLink()

    def isFolded(self):
        return self.folded

    def getStyle(self):
        return "padding-left: %dpx" % (self.indent * 6)

    def getText(self, accessdata=None):
        if accessdata is not None:
            warn("accessdata argument is unused, remove it", DeprecationWarning)
        try:
            if isinstance(self.node, Directory):
                if self.count == -1:
                    self.count = self.node.content_children_for_all_subcontainers.distinct().count()

                if self.hide_empty and self.count == 0:
                    return ""  # hides entry
            else:
                if hasattr(self.node, "childcount"):
                    self.count = self.node.childcount()

            if self.count > 0:
                return u"%s <small>(%s)</small>" % (self.node.getLabel(lang=self.lang), unicode(self.count))
            else:
                return self.node.getLabel(lang=self.lang)

        except:
            logg.exception("exception in NavTreeEntry.getText, return Node (0)")
            return "Node (0)"

    def getClass(self):
        if self.node.type == "directory":
            return "lv2"
        else:
            if self.indent > 1:
                return "lv1"
            else:
                return "lv0"


class RecursionException:
    pass


class Collectionlet(Portlet):

    def __init__(self):
        Portlet.__init__(self)
        self.name = "collectionlet"
        self.collection = q(Collections).one()
        self.directory = self.collection
        self.folded = 0
        self.col_data = None
        self.hassubdir = 0
        self.hide_empty = False

    def getCurrent(self):
        return self.collection

    def feedback(self, req):
        Portlet.feedback(self, req)
        self.lang = lang(req)
        # XXX: node refreshing, better save node ids
        self.collection = db.refresh(self.collection)
        self.directory = db.refresh(self.directory)
        if "dir" in req.params or "id" in req.params:
            id = req.params.get("id", req.params.get("dir"))
            node = q(Node).get(id)
            if node is not None:
                if isCollection(node):
                    self.collection = node
                    self.directory = node
                else:
                    if isDirectory(node):
                        self.directory = node
                    else:
                        # XXX: do we really need these checks? Better way?
                        if not isDirectory(self.directory) or not node.is_descendant_of(self.directory):
                            self.directory = getDirectory(node)
                    if isinstance(self.collection, Collections) or not node.is_descendant_of(self.collection):
                        self.collection = getCollection(node)
        try:
            self.hide_empty = self.collection.get("style_hide_empty") == "1"
        except:
            self.hide_empty = False
        # open all parents, so we see that node
        opened = {}
        parents = [self.directory]
        counter = 0
        while parents:
            counter += 1
            if counter > 50:
                raise RecursionException
            p = parents.pop()
            opened[p.id] = 1
            parents.extend(p.parents)

        m = {}

        def f(m, node, indent, hide_empty):
            if indent > 15:
                raise RecursionException
            if not isinstance(node, (Root, Collections)) and not node.has_read_access():
                return

            m[node.id] = e = NavTreeEntry(self, node, indent, node.type == "directory", hide_empty=hide_empty, lang=self.lang)
            if node.id in opened or e.defaultopen:
                m[node.id].folded = 0
                for c in node.getContainerChildren():
                    if c.get("style_hide_empty") == "1":
                        hide_empty = 1
                    f(m, c, indent + 1, hide_empty)

        f(m, q(Collections).one(), 0, self.hide_empty)

        if "cunfold" in req.params:
            id = req.params["cunfold"]
            if id in m:
                m[id].folded = 0

        if self.directory.id in m:
            m[self.directory.id].folded = 0
            m[self.directory.id].active = 1

        if self.collection.id in m:
            m[self.collection.id].active = 1

        col_data = []

        def f(col_data, node, indent):
            if indent > 15:
                raise RecursionException
            if node.id not in m:
                return

            data = m[node.id]
            col_data += [data]
            if not data.folded or data.defaultopen:
                for c in node.getContainerChildren().sort_by_orderpos():
                    f(col_data, c, indent + 1)

        f(col_data, q(Collections).one(), 0)
        self.col_data = col_data

    def getCollections(self):
        return self.col_data

    def getCollUnfold(id):
        if self.req.params.get("colunfold", "") == ustr(id):
            return True
        else:
            return False


class Pathlet:

    def __init__(self, currentdir):
        self.currentdir = currentdir

    def getPath(self):
        path = []
        if isinstance(self.currentdir, type("")):
            path.append(Link(self.currentdir, self.currentdir, self.currentdir))
        else:
            cd = self.currentdir
            if cd is not None:
                path.append(Link('', cd.name, ''))
                while True:
                    parents = cd.getParents()
                    if(len(parents) == 0):
                        break
                    cd = parents[0]
                    if cd is tree.getRoot():
                        break
                    path.append(Link('/?id=' + cd.id + '&dir=' + cd.id, cd.name, cd.name))
        path.reverse()


class CollectionMapping:

    def __init__(self):
        self.searchmap = {}
        self.browsemap = {}

    def getSearch(self, collection):
        if collection.id not in self.searchmap:
            self.searchmap[collection.id] = Searchlet(collection)
        return self.searchmap[collection.id]


def getSessionSetting(req, name, default):
    try:
        value = req.params[name]
        value[0]
    except:
        pass
    try:
        value = req.session[name]
    except:
        value = default
        req.session[name] = default

    return value


class UserLinks:

    def __init__(self, user, area="", host=""):
        self.user = user
        self.id = None
        self.language = ""
        self.area = area
        self.host = host

    def feedback(self, req):
        if "id" in req.params:
            self.id = req.params.get("id")
        self.language = lang(req)

    def getLinks(self):
        guest_user = get_guest_user()
        l = [Link("/logout", t(self.language, "sub_header_logout_title"),
                  t(self.language, "sub_header_logout"), icon="/img/logout.gif")]
        if  self.user is guest_user:
            if config.get("config.ssh") == "yes":
                host = config.get("host.name") or self.host
                l = [Link("https://" + host + "/login", t(self.language, "sub_header_login_title"),
                          t(self.language, "sub_header_login"), icon="/img/login.gif")]
            else:
                l = [Link("/login", t(self.language, "sub_header_login_title"),
                          t(self.language, "sub_header_login"), icon="/img/login.gif")]

        if self.area != "":
            l += [Link("/", t(self.language, "sub_header_frontend_title"),
                       t(self.language, "sub_header_frontend"), icon="/img/frontend.gif")]

        if self.user.is_editor:
            idstr = ""
            if self.id:
                idstr = "?id=" + unicode(self.id)
            l += [Link("/edit" + idstr, t(self.language, "sub_header_edit_title"),
                       t(self.language, "sub_header_edit"), icon="/img/edit.gif")]

        if self.user.is_admin:
            l += [Link("/admin", t(self.language, "sub_header_administration_title"),
                       t(self.language, "sub_header_administration"), icon="/img/admin.gif")]

        if self.user.is_workflow_editor:
            l += [Link("/publish/", t(self.language, "sub_header_workflow_title"),
                       t(self.language, "sub_header_workflow"), icon="/img/workflow.gif")]

        if self.user.can_change_password:
            l += [Link("/pwdchange", t(self.language, "sub_header_changepwd_title"),
                       t(self.language, "sub_header_changepwd"), "_parent", icon="/img/changepwd.gif")]
        return l


class NavigationFrame:

    def __init__(self):
        self.cmap = CollectionMapping()
        self.collection_portlet = Collectionlet()

    def feedback(self, req):
        user = users.getUserFromRequest(req)

        host = req.get_header("HOST")
        userlinks = UserLinks(user, area=req.session.get("area"), host=host)
        userlinks.feedback(req)

        # tabs
        navigation = {}

        # collection
        collection_portlet = self.collection_portlet
        collection_portlet.feedback(req)
        col_selected = collection_portlet.collection
        navigation["collection"] = collection_portlet

        # search
        search_portlet = self.cmap.getSearch(col_selected)
        search_portlet.feedback(req)
        navigation["search"] = search_portlet

        # languages
        front_lang = {}
        front_lang["name"] = config.languages
        front_lang["actlang"] = lang(req)

        self.params = {"show_navbar": True, "user": user, "userlinks": userlinks, "navigation": navigation, "language": front_lang}

    def write(self, req, contentHTML, show_navbar=1):
        self.params["show_navbar"] = show_navbar
        self.params["content"] = contentHTML
        self.params["act_node"] = req.params.get("id", req.params.get("dir", ""))

        rootnode = q(Collections).one()
        self.params["header_items"] = rootnode.getCustomItems("header")
        self.params["footer_left_items"] = rootnode.getCustomItems("footer_left")
        self.params["footer_right_items"] = rootnode.getCustomItems("footer_right")
        self.params["t"] = time.strftime("%d.%m.%Y %H:%M:%S")
        self.params["head_meta"] = req.params.get('head_meta', '')

        # header
        self.params["header"] = req.getTAL(theme.getTemplate("frame.html"), self.params, macro="frame_header")

        # footer
        self.params["footer"] = req.getTAL(theme.getTemplate("frame.html"), self.params, macro="frame_footer")

        self.params["tree"] = ""
        self.params["search"] = ""
        if show_navbar == 1:
            # search mask
            self.params["search"] = req.getTAL(
                theme.getTemplate("frame.html"), {
                    "search": self.params["navigation"]["search"], "act_node": self.params["act_node"]}, macro="frame_search")

            # tree
            self.params["tree"] = req.getTAL(
                theme.getTemplate("frame.html"), {
                    "collections": self.collection_portlet.getCollections()}, macro="frame_tree")

        req.writeTAL(theme.getTemplate("frame.html"), self.params, macro="frame")


def getNavigationFrame(req):
    return NavigationFrame()
