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
from warnings import warn
from sqlalchemy import event
from markupsafe import Markup

import core.config as config
from core import db, Node
from core.translation import lang, t
from core.metatype import Context
from core import webconfig
from core.users import user_from_session as _user_from_session
from core.users import get_guest_user
from core.webconfig import node_url, edit_node_url
from contenttypes import Directory, Container, Collection, Collections
from schema.schema import getMetadataType
from utils.compat import iteritems
from utils.utils import Link
from utils.url import build_url_from_path_and_params
from schema.searchmask import SearchMask
from mediatumtal import tal
import core.nodecache as _nodecache
from core.nodecache import get_collections_node
import time


q = db.query
logg = logging.getLogger(__name__)


def getSearchMask(collection):
    if collection.get("searchtype") == "none":
        return None
    mask = None
    n = collection
    if collection.get("searchtype") == "parent":
        while len(n.parents):
            if n.get("searchtype") == "own":
                break
            n = n.parents[0]
    if n.get("searchtype") == "own":
        mask = q(SearchMask).filter_by(name=n.get("searchmaskname")).scalar()
    return mask


class Searchlet(object):

    def __init__(self, container, edit=False):
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
        self.edit = edit

        if self.searchmask:
            for field in self.searchmask.children.order_by("orderpos"):
                self.searchmaskitems[field.id] = field.name
        self.searchmaskitem_ids = [None] * 11

    def feedback(self, req):
        self.lang = lang(req)
        self.ip = req.remote_addr
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

        # this is the "special" value for simple search
        if not extendedfields and "query" in req.args:
            self.values[0] = req.args["query"]
        else:
            for pos in extendedfields:
                searchmaskitem_argname = "field" + str(pos)
                searchmaskitem_id = req.args.get(searchmaskitem_argname, type=int)
                self.searchmaskitem_ids[pos] = searchmaskitem_id

                searchmaskitem = self.searchmask.children.filter_by(id=searchmaskitem_id).scalar() if searchmaskitem_id else None
                field = searchmaskitem.children.first() if searchmaskitem else None

                value_argname = "query" + str(pos)

                if field is not None and field.getFieldtype() == "date":
                    from_value = req.args.get(value_argname + "-from", u"")
                    to_value = req.args.get(value_argname + "-to", u"")
                    value = from_value + ";" + to_value
                else:
                    value = req.args.get(value_argname)

                if value:
                    self.values[pos] = value

    def hasExtendedSearch(self):
        return self.searchmask is not None

    @property
    def simple_search_query(self):
        return self.values[0]

    def search_link(self, mode="simple"):
        params = {k: v for k, v in iteritems(self.url_params) if k not in ("query", "searchmode", "id")}
        if mode != "simple":
            params["searchmode"] = mode

        return node_url(self.container.id, **params) if not self.edit else edit_node_url(self.container.id, **params)

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

    def inEditor(self):
        return self.edit

    def getSearchField(self, pos, width=174):
        user = _user_from_session()
        try:
            searchmaskitem_id = self.searchmaskitem_ids[pos]
            searchmaskitem = self.searchmask.children.filter_by(id=searchmaskitem_id).scalar() if searchmaskitem_id else None
            field = searchmaskitem.children.first() if searchmaskitem else None
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
                user=user,
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


def render_search_box(container, language, req, edit=False):
    search_portlet = Searchlet(container, edit)
    search_portlet.feedback(req)
    liststyle = req.args.get("liststyle")

    ctx = {
        "search": search_portlet,
        "container_id": container.id,
        "liststyle": liststyle,
        "language": language,
        "search_placeholder": t(language, "search_in") + " " + container.getLabel(language),
        "action": '/' if not edit else '/edit/edit_content',
    }

    search_html = webconfig.theme.render_template("frame_search.j2.jade", ctx)

    return search_html


def render_edit_search_box(container, language, req, edit=False):
    search_portlet = Searchlet(container, edit)
    search_portlet.feedback(req)
    liststyle = req.args.get("liststyle")

    ctx = {
        "search": search_portlet,
        "container_id": container.id,
        "liststyle": liststyle,
        "language": language,
        "search_placeholder": t(language, "search_in") + " " + container.getLabel(language),
        "action": '/' if not edit else '/edit/edit_content',
    }

    search_html = webconfig.theme.render_template("edit_search.j2.jade", ctx)

    return search_html


class NavTreeEntry(object):

    def __init__(self, node, indent, small=0, hide_empty=0, lang=None):
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
        self.hide_empty = hide_empty
        self.lang = lang
        self.orderpos = 0
        self.show_childcount = node.show_childcount

        self.count = self.node.childcount()

        if self.count:
            self.hassubdir = 1
            self.folded = 1

    def getFoldLink(self):
        return self.getLink()

    def getUnfoldLink(self):
        return self.getLink()

    def getLink(self):
        return node_url(self.node.id)

    def isFolded(self):
        return self.folded

    def getStyle(self):
        return "padding-left: %dpx" % (self.indent * 6)

    def getText(self, accessdata=None):
        if accessdata is not None:
            warn("accessdata argument is unused, remove it", DeprecationWarning)
        try:
            if self.hide_empty and self.count == 0:
                return ""  # hides entry

            if self.show_childcount and self.count > 0:
                return Markup(u"%s <small>(%s)</small>" % (self.node.getLabel(lang=self.lang), unicode(self.count)))
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


def find_collection_and_container(node_id):
    
    node = q(Node).get(node_id) if node_id else None
    
    if node is None:
        collection = get_collections_node()
        container = collection

    else:
        if isinstance(node, Container):
            container = node

            if isinstance(node, Collection):  # XXX: is Collections also needed here?
                collection = node
            else:
                collection = node.get_collection()
        else:
            container = node.get_container()
            collection = node.get_collection()

    return collection, container


def make_navtree_entries(language, collection, container):
    hide_empty = collection.get("style_hide_empty") == "1"

    opened = {t[0] for t in container.all_parents.with_entities(Node.id)}
    opened.add(container.id)

    navtree_entries = []

    def make_navtree_entries_rec(navtree_entries, node, indent, hide_empty):
        small = not isinstance(node, (Collection, Collections))
        e = NavTreeEntry(node, indent, small, hide_empty, language)
        if node.id == collection.id or node.id == container.id:
            e.active = 1
        navtree_entries.append(e)
        if node.id in opened:
            e.folded = 0
            """
            find children ids for a given node id for an additional filter to determine the container_children
            important: this additional filter is logical not needed - but it speeds up the computation of the
                       container_children especially for guest users
                       this additional filter is only used if the number of children ids is lower than 100
            """
            children_ids = db.session.execute("select cid from nodemapping where nid = %d" % node.id)
            cids = [row['cid'] for row in children_ids]
            if len(cids) < 100:
                container_children = node.container_children.filter(Node.id.in_(cids)).filter_read_access().order_by(Node.orderpos).prefetch_attrs()
            else:
                container_children = node.container_children.filter_read_access().order_by(Node.orderpos).prefetch_attrs()
            for c in container_children:
                if hasattr(node, "dont_ask_children_for_hide_empty"):
                    style_hide_empty = hide_empty
                else:
                    style_hide_empty = c.get("style_hide_empty") == "1"

                make_navtree_entries_rec(navtree_entries, c, indent + 1, style_hide_empty)

    collections_root = get_collections_node()

    if collections_root is not None:
        time0 = time.time()
        make_navtree_entries_rec(navtree_entries, collections_root, 0, hide_empty)
        time1 = time.time()
        logg.info("make_navtree_entries: %f", time1 - time0)

    return navtree_entries


def _render_navtree_cached_for_anon(language, node_id):
    """
    XXX: This can be improved to reduce the number of stored trees. 
    Trees for sibling containers without own container children are the same except for the directory / collection highlighting.
    Maybe we can store a generic tree for all of them and just set the highlighting here?

    TODO: cache invalidation / timeout
    """
    return _render_navtree(language, node_id)


def _render_navtree(language, node_id):
    collection, container = find_collection_and_container(node_id)
    navtree_entries = make_navtree_entries(language, collection, container)
    if navtree_entries:
        html = webconfig.theme.render_template("frame_tree.j2.jade", {"navtree_entries": navtree_entries})
    else:
        html = u""
    logg.debug("rendered navtree with %s unicode chars", len(html))
    return html


def render_navtree(language, node_id, user):
    """Renders the navigation tree HTML.
    Results are cached (key is (language, node_id)) for anonymous users only. 
    They all see the same tree, so it's feasible to cache the HTML.
    """
    if user.is_anonymous:
        html = _render_navtree_cached_for_anon(language, node_id)
        return html
    else:
        return _render_navtree(language, node_id)

class UserLinks(object):

    def __init__(self, user, req):
        self.user = user
        self.host = req.host
        # show_id: edit currently shown content node
        nid = req.args.get("show_id")
        # id: edit current container
        if nid is None:
            nid = req.args.get("id")

        self.id = nid
        self.language = lang(req)
        self.path = req.mediatum_contextfree_path
        self.args = req.args
        # XXX: hack to show the frontend link when workflows are displayed
        self.is_workflow_area = req.mediatum_contextfree_path.startswith("/publish")

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

        if self.is_workflow_area:
            l += [Link("/", t(self.language, "sub_header_frontend_title"),
                       t(self.language, "sub_header_frontend"), icon="/img/frontend.gif")]

        if self.user.is_editor:
            idstr = ""
            if self.id:
                idstr = "?id=" + unicode(self.id)
            # set edit-link to upload_dir if user comes from collections
            if not self.id or int(self.id) == get_collections_node().id:
                if self.user.upload_dir:
                    idstr = "?id=" + unicode(self.user.upload_dir.id)
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


def _render_head_meta(node):
    """
    create meta tags for google_scholar by using the exportmask head_meta

    :param node:
    :return: rendered head_meta mask
    """
    if config.get("websearch.google_scholar", "").lower() == "true" or not node or node.isContainer():
        mtype = _nodecache.get_metadatatypes_node().children.filter_by(name=node.schema).scalar()
        mask = mtype and mtype.getMask('head_meta')
        return mask and mask.getViewHTML([node], flags=8)


def render_page(req, node, content_html, show_navbar=True, show_id=None):
    """Renders the navigation frame with the inserted content HTML and returns the whole page.
    """
    user = _user_from_session()
    userlinks = UserLinks(user, req)
    language = lang(req)
    rootnode = get_collections_node()

    if node is None:
        node = rootnode
        container = rootnode
    else:
        container = node.get_container()
    
    theme = webconfig.theme

    front_lang = {
        "name": config.languages,
        "actlang": language
    }
    frame_context = {
        "content": Markup(content_html),
        "id": node.id,
        "language": front_lang,
        "show_navbar": show_navbar,
    }

    search_html = u""
    navtree_html = u""

    if show_navbar and not req.args.get("disable_navbar"):
        if not req.args.get("disable_search"):
            search_html = render_search_box(container, language, req)

        if not req.args.get("disable_navtree"):
            navtree_html = render_navtree(language, node.id, user)

    ctx_header = {
        "user_name": user.getName(),
        "userlinks": userlinks,
        "header_items": rootnode.getCustomItems("header"),
        "language": front_lang,
        "show_language_switcher": (len(front_lang['name']) > 1)
    }
    header_html = theme.render_template("frame_header.j2.jade", ctx_header)

    ctx_footer = {
        "footer_left_items": rootnode.getCustomItems("footer_left"),
        "footer_right_items": rootnode.getCustomItems("footer_right")
    }
    footer_html = theme.render_template("frame_footer.j2.jade", ctx_footer)

    frame_context["search"] = Markup(search_html)
    frame_context["navtree"] = Markup(navtree_html)
    frame_context["header"] = Markup(header_html)
    frame_context["footer"] = Markup(footer_html)

    if show_id and isinstance(show_id, list):
        show_id = show_id[0]
    else:
        show_id = req.args.get("show_id")
    if show_id:
        shown_node = q(Node).get(show_id)
    else:
        shown_node = node
    frame_context["google_scholar"] = _render_head_meta(shown_node) or ""

    html = theme.render_template("frame.j2.jade", frame_context)

    return html
