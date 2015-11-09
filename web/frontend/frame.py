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
import urllib
from warnings import warn
from sqlalchemy import event

import core.config as config
from core import db, users
from core import Node
from core.translation import lang, t
from core.metatype import Context
from core.styles import theme
from core.systemtypes import Searchmasks, Root
from core.users import get_guest_user
from contenttypes import Directory, Container, Collections, Collection
from schema.schema import getMetadataType
from utils.compat import iteritems
from utils.utils import Link

q = db.query
logg = logging.getLogger(__name__)


class Portlet:

    def __init__(self):
        self.folded = 0
        self.name = "common"
        self.user = get_guest_user()

    def isFolded(self):
        warn("use Portlet.folded()", DeprecationWarning)
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
        # get searchfields for collection
        self.searchfields = OrderedDict()

        if self.searchmask:
            for field in self.searchmask.getChildren().sort_by_orderpos():
                self.searchfields[field.id] = field.name
        self.names = [None] * 11

    def feedback(self, req):
        Portlet.feedback(self, req)
        self.req = req
        self.url_params = {k: v for k, v in iteritems(req.args) if k not in ()}

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

    def search_link(self, mode="simple"):
        params = {k: v for k, v in iteritems(self.url_params) if k not in ("query", "searchmode")}
        if mode != "simple":
            params["searchmode"] = mode

        return u"node?" + urllib.urlencode(params)

    def searchLinkSimple(self):
        return self.search_link()

    def searchLinkExtended(self):
        return self.search_link("extended")

    def searchLinkExtendedSuper(self):
        return self.search_link("extendedsuper")

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


# XXX very simple and conservative directory child count cache. Cleared after each commit.
directory_child_count_cache = {}

@event.listens_for(db.Session, "after_commit")
def clear_directory_child_count_cache_after_commit(session):
    directory_child_count_cache.clear()


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

    def getFoldLink(self):
        return self.getLink()

    def getUnfoldLink(self):
        return self.getLink()

    def getLink(self):
        return u"/node?id=" + unicode(self.node.id)

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
                    if self.id in directory_child_count_cache:
                        self.count = directory_child_count_cache[self.id]
                    else:
                        directory_child_count_cache[self.id] = self.count = self.node.content_children_for_all_subcontainers.count()

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
        if isinstance(self.node, Directory):
            return "lv2"
        else:
            if self.indent > 1:
                return "lv1"
            else:
                return "lv0"


class Collectionlet(Portlet):

    def __init__(self):
        Portlet.__init__(self)
        self.name = "collectionlet"
        self.collection = None
        self.directory = None
        self.folded = 0
        self.col_data = None
        self.hassubdir = 0
        self.hide_empty = False

    def feedback(self, req):
        Portlet.feedback(self, req)
        self.lang = lang(req)
        nid = req.args.get("id", type=int)
        if nid:
            node = q(Node).get(nid)
            if node is not None:
                if isinstance(node, Container):
                    self.directory = node

                    if isinstance(node, Collection): # XXX: is Collections also needed here?
                        self.collection = node
                    else:
                        self.collection = node.get_parent_collection()
                else:
                    self.directory = node.get_parent_container()
                    self.collection = node.get_parent_collection()

        if self.collection is None:
            self.collection = q(Collections).one()
            self.directory = self.collection

        self.hide_empty = self.collection.get("style_hide_empty") == "1"

        opened = {t[0] for t in self.directory.all_parents.with_entities(Node.id)}
        opened.add(self.directory.id)

        col_data = []

        def f(m, node, indent, hide_empty):
            if not isinstance(node, (Root, Collections)) and not node.has_read_access():
                return

            small = not isinstance(node, (Collection, Collections))
            e = NavTreeEntry(self, node, indent, small, hide_empty, self.lang)
            if node.id == self.collection.id or node.id == self.directory.id:
                e.active = 1
            m.append(e)
            if node.id in (self.directory.id, self.collection.id) or node.id in opened or e.defaultopen:
                e.folded = 0
                for c in node.container_children.order_by(Node.orderpos).prefetch_attrs():
                    if c.get("style_hide_empty") == "1":
                        hide_empty = 1
                    f(m, c, indent + 1, hide_empty)

        f(col_data, q(Collections).one(), 0, self.hide_empty)

        self.col_data = col_data

    def getCollections(self):
        return self.col_data


class CollectionMapping:

    def __init__(self):
        self.searchmap = {}
        self.browsemap = {}

    def getSearch(self, collection):
        if collection.id not in self.searchmap:
            self.searchmap[collection.id] = Searchlet(collection)
        return self.searchmap[collection.id]


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
        self.params["id"] = req.params.get("id", req.params.get("dir", ""))

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
            # collection_id specifies which collection to search
            collection = self.collection_portlet.collection
            ctx = {
                "search": self.params["navigation"]["search"],
                "collection_id": None
            }
            # we want to search to current collection except when it's the collection root
            if not isinstance(collection, Collections):
                ctx["collection_id"] = collection.id

            self.params["search"] = req.getTAL(theme.getTemplate("frame.html"), ctx, macro="frame_search")

            # tree
            self.params["tree"] = req.getTAL(
                theme.getTemplate("frame.html"), {
                    "collections": self.collection_portlet.getCollections()}, macro="frame_tree")

        req.writeTAL(theme.getTemplate("frame.html"), self.params, macro="frame")


def getNavigationFrame(req):
    return NavigationFrame()
