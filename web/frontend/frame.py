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
from core.transition import current_user
from core.users import get_guest_user
from core.webconfig import node_url
from contenttypes import Directory, Container, Collections, Collection
from schema.schema import getMetadataType
from utils.compat import iteritems
from utils.utils import Link
from utils.url import build_url_from_path_and_params


q = db.query
logg = logging.getLogger(__name__)

child_count_cache = None


def init_child_count_cache():
    """XXX very simple and conservative directory child count cache. Cleared after each commit.
    """
    global child_count_cache
    child_count_cache = {}

    @event.listens_for(db.Session, "after_commit")
    def clear_directory_child_count_cache_after_commit(session):
        child_count_cache.clear()


class Portlet(object):

    def __init__(self):
        self.folded = 0
        self.name = "common"
        self._user = None

    @property
    def user(self):
        if self._user is None:
            logg.warn("accessed Portlet.user but it's not set; using guest user. Is that correct?")
            self._user = get_guest_user()
        return self._user

    @user.setter
    def user(self, user):
        self._user = user

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
        self.user = current_user
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

    def __init__(self, container):
        Portlet.__init__(self)
        self.lang = None
        self.ip = None
        self.container = container
        # Searchmasks are defined on collections, so we must find the parent collection if container is not a collection.
        collection = container.get_collection()
        self.searchmask = getSearchMask(collection)
        self.searchmode = "simple"

        self.values = [None] + [""] * 10
        self.req = None
        self.searchmaskitems = OrderedDict()

        if self.searchmask:
            for field in self.searchmask.children.order_by("orderpos"):
                self.searchmaskitems[field.id] = field.name
        self.searchmaskitem_ids = [None] * 11

    def feedback(self, req):
        Portlet.feedback(self, req)
        self.lang = lang(req)
        self.ip = req.ip
        self.url_params = {k: v for k, v in iteritems(req.args) if k not in ()}

        searchmode_from_req = req.args.get("searchmode")
        if searchmode_from_req in ("extended", "extendedsuper"):
            if self.searchmask is None:
                raise ValueError("no searchmask defined, extended search cannot be run for container {}".format(self.container.id))
            self.searchmode = searchmode_from_req


        if self.searchmode == "extended":
            extendedfields = range(1, 4)
        elif self.searchmode == "extendedsuper":
            extendedfields = range(1, 11)
        else:
            extendedfields = []

        for pos in extendedfields:
            searchmaskitem_argname = "field" + str(pos)
            searchmaskitem_id = req.args.get(searchmaskitem_argname, type=int)
            self.searchmaskitem_ids[pos] = searchmaskitem_id

            searchmaskitem = self.searchmask.children.filter_by(id=searchmaskitem_id).scalar() if searchmaskitem_id else None
            field = searchmaskitem.children.scalar() if searchmaskitem else None

            if field is not None:
                value_argname = "query" + str(pos)
                if field.getFieldtype() == "date":
                    from_value = req.args.get(value_argname + "-from", "")
                    to_value = req.args.get(value_argname + "-to", "")
                    value = from_value + ";" + to_value
                else:
                    value = req.args.get(value_argname)

                if value:
                    self.values[pos] = value

        # this is the "special" value for simple search
        if not extendedfields and "query" in req.args:
            self.values[0] = req.args["query"]

    def hasExtendedSearch(self):
        return self.searchmask is not None

    @property
    def simple_search_query(self):
        return self.values[0]

    def search_link(self, mode="simple"):
        params = {k: v for k, v in iteritems(self.url_params) if k not in ("query", "searchmode")}
        if mode != "simple":
            params["searchmode"] = mode

        return node_url(**params)

    def searchLinkSimple(self):
        return self.search_link()

    def searchLinkExtended(self):
        return self.search_link("extended")

    def searchLinkExtendedSuper(self):
        return self.search_link("extendedsuper")

    def isSimple(self):
        return self.searchmode == "simple"

    def isExtendedNormal(self):
        return self.searchmode == "extended"

    def isExtendedSuper(self):
        return self.searchmode == "extendedsuper"

    def getSearchField(self, pos, width=174):
        try:
            searchmaskitem_id = self.searchmaskitem_ids[pos]
            searchmaskitem = self.searchmask.children.filter_by(id=searchmaskitem_id).scalar() if searchmaskitem_id else None
            field = searchmaskitem.children.scalar() if searchmaskitem else None
            g = None
            if field is None:  # All Metadata
                # quick&dirty
                field = getMetadataType("text")
            return field.getSearchHTML(Context(
                                            field,
                                            value=self.values[pos],
                                            width=width,
                                            name="query" + unicode(pos),
                                            language=self.lang,
                                            container=self.container,
                                            user=current_user,
                                            ip=self.ip))
        except:
            # workaround for unknown error
            logg.exception("exception in getSearchField, return empty string")
            return ""

    def searchmaskitem_is_selected(self, pos, searchmaskitem_id):
        if self.searchmaskitem_ids[pos] == searchmaskitem_id:
            return "selected"
        else:
            None


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
        # do we really need this '#' ?
        return node_url(self.node.id) + "#" + str(self.node.id)

    def isFolded(self):
        return self.folded

    def getStyle(self):
        return "padding-left: %dpx" % (self.indent * 6)

    def getText(self, accessdata=None):
        if accessdata is not None:
            warn("accessdata argument is unused, remove it", DeprecationWarning)
        try:
            if self.count == -1:
                if isinstance(self.node, Directory):
                    if self.id in child_count_cache:
                        self.count = child_count_cache[self.id]
                    else:
                        child_count_cache[self.id] = self.count = self.node.childcount()

                    if self.hide_empty and self.count == 0:
                        return ""  # hides entry

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
        self.container = None
        self.folded = 0
        self.col_data = None
        self.hassubdir = 0
        self.hide_empty = False

    @property
    def directory(self):
        warn("use Collectionlet.container instead", DeprecationWarning)
        return self.container

    def feedback(self, req):
        Portlet.feedback(self, req)
        self.lang = lang(req)
        nid = req.args.get("id", type=int)
        if nid:
            node = q(Node).get(nid)
            if node is not None:
                if isinstance(node, Container):
                    self.container = node

                    if isinstance(node, Collection): # XXX: is Collections also needed here?
                        self.collection = node
                    else:
                        self.collection = node.get_collection()
                else:
                    self.container = node.get_container()
                    self.collection = node.get_collection()

        if self.collection is None:
            self.collection = q(Collections).one()
            self.container = self.collection

        self.hide_empty = self.collection.get("style_hide_empty") == "1"

        opened = {t[0] for t in self.container.all_parents.with_entities(Node.id)}
        opened.add(self.container.id)

        col_data = []

        def f(m, node, indent, hide_empty):
            if not isinstance(node, (Root, Collections)) and not node.has_read_access():
                return

            small = not isinstance(node, (Collection, Collections))
            e = NavTreeEntry(self, node, indent, small, hide_empty, self.lang)
            if node.id == self.collection.id or node.id == self.container.id:
                e.active = 1
            m.append(e)
            if node.id in (self.container.id, self.collection.id) or node.id in opened or e.defaultopen:
                e.folded = 0
                for c in node.container_children.order_by(Node.orderpos).prefetch_attrs():
                    f(m, c, indent + 1, c.get("style_hide_empty") == "1")

        f(col_data, q(Collections).one(), 0, self.hide_empty)

        self.col_data = col_data

    def getCollections(self):
        return self.col_data


class UserLinks(object):

    def __init__(self, user, area="", host=""):
        self.user = user
        self.id = None
        self.language = ""
        self.area = area
        self.host = host

    def feedback(self, req):
        # show_id: edit currently shown content node
        nid = req.args.get("show_id")
        # id: edit current container
        if nid is None:
            nid = req.args.get("id")

        self.id = nid
        self.language = lang(req)
        self.path = req.path
        self.args = req.args

    def getLinks(self):
        guest_user = get_guest_user()
        l = [Link("/logout", t(self.language, "sub_header_logout_title"),
                  t(self.language, "sub_header_logout"), icon="/img/logout.gif")]
        if self.user == guest_user:
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

    def change_language_link(self, language):
        params = self.args.copy()
        params["change_language"] = language
        return build_url_from_path_and_params(self.path, params)


class NavigationFrame(object):

    def __init__(self):
        self.collection_portlet = Collectionlet()

    def feedback(self, req):
        user = current_user

        host = req.get_header("HOST")
        userlinks = UserLinks(user, area=req.session.get("area"), host=host)
        userlinks.feedback(req)

        # tabs
        navigation = {}

        # collection
        collection_portlet = self.collection_portlet
        collection_portlet.feedback(req)
        navigation["collection"] = collection_portlet

        # search
        search_portlet = Searchlet(collection_portlet.container)
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
        self.params["id"] = nid = req.params.get("id", req.params.get("dir", ""))

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
            container = q(Container).get(nid) if nid else None
            if container is None:
                container = rootnode
            language = lang(req)

            ctx = {
                "search": self.params["navigation"]["search"],
                "container_id": container.id,
                "search_placeholder": t(language, "search_in") + " " + container.getLabel(language)
            }

            self.params["search"] = req.getTAL(theme.getTemplate("frame.html"), ctx, macro="frame_search")

            # tree
            self.params["tree"] = req.getTAL(
                theme.getTemplate("frame.html"), {
                    "collections": self.collection_portlet.getCollections()}, macro="frame_tree")

        req.writeTAL(theme.getTemplate("frame.html"), self.params, macro="frame")


def getNavigationFrame(req):
    return NavigationFrame()
