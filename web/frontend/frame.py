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
from dogpile.cache import make_region
from sqlalchemy import event

import core.config as config
from core import db, Node
from core.translation import lang, t
from core.metatype import Context
from core import webconfig
from core.transition import current_user
from core.users import get_guest_user
from core.webconfig import node_url
from contenttypes import Directory, Container, Collection, Collections
from schema.schema import getMetadataType
from utils.compat import iteritems
from utils.utils import Link
from utils.url import build_url_from_path_and_params
from schema.searchmask import SearchMask
from mediatumtal import tal
from core.nodecache import get_collections_node


navtree_cache = make_region().configure(
    'dogpile.cache.redis',
    expiration_time=5 * 60, # 10 mins and one second
    arguments = {
        'db': 1,
        'redis_expiration_time': 5 * 60 + 10,
        'distributed_lock': False
    }                                     
)

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

    def __init__(self, container):
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


def render_search_box(container, language, req):
    search_portlet = Searchlet(container)
    search_portlet.feedback(req)
    liststyle = req.args.get("liststyle")

    ctx = {
        "search": search_portlet,
        "container_id": container.id,
        "liststyle": liststyle,
        "search_placeholder": t(language, "search_in") + " " + container.getLabel(language)
    }

    search_html = tal.getTAL(webconfig.theme.getTemplate("frame.html"), ctx, macro="frame_search", language=language)
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

        if self.id in child_count_cache:
            self.count = child_count_cache[self.id]
        else:
            child_count_cache[self.id] = self.count = self.node.childcount()

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
            for c in node.container_children.filter_read_access().order_by(Node.orderpos).prefetch_attrs():
                if hasattr(node, "dont_ask_children_for_hide_empty"):
                    style_hide_empty = hide_empty
                else:
                    style_hide_empty = c.get("style_hide_empty") == "1"

                make_navtree_entries_rec(navtree_entries, c, indent + 1, style_hide_empty)

    collections_root = get_collections_node()

    if collections_root is not None:
        make_navtree_entries_rec(navtree_entries, collections_root, 0, hide_empty)

    return navtree_entries


@navtree_cache.cache_on_arguments()
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
    html = tal.getTAL(webconfig.theme.getTemplate("frame.html"), {"navtree_entries": navtree_entries}, macro="frame_tree", language=language)
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
        self.host = req.get_header("HOST")
        # show_id: edit currently shown content node
        nid = req.args.get("show_id")
        # id: edit current container
        if nid is None:
            nid = req.args.get("id")

        self.id = nid
        self.language = lang(req)
        self.path = req.path
        self.args = req.args
        # XXX: hack to show the frontend link when workflows are displayed
        self.is_workflow_area = req.path.startswith("/publish")

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


def render_page(req, node, contentHTML, show_navbar=True):
    """Renders the navigation frame with the inserted content HTML and returns the whole page.
    """
    user = current_user
    userlinks = UserLinks(user, req)
    language = lang(req)
    rootnode = get_collections_node()
    
    if node is None:
        node = rootnode
        container = rootnode
    else:
        container = node.get_container()
    
    frame_template = webconfig.theme.getTemplate("frame.html")

    front_lang = {
        "name": config.languages,
        "actlang": language
    }
    frame_context = {
        "content": contentHTML,
        "footer_left_items": rootnode.getCustomItems("footer_left"),
        "footer_right_items": rootnode.getCustomItems("footer_right"),
        "header_items": rootnode.getCustomItems("header"),
        "id": node.id,
        "language": front_lang,
        "show_navbar": show_navbar,
        "user": user, 
        "userlinks": userlinks
    }

    navtree_html = u""
    search_html = u""

    if show_navbar and not req.args.get("disable_navbar"):
        if not req.args.get("disable_search"):
            search_html = render_search_box(container, language, req)

        if not req.args.get("disable_navtree"):
            navtree_html = render_navtree(language, node.id, user)

    frame_context["search"] = search_html
    frame_context["tree"] = navtree_html
    frame_context["footer"] = tal.getTAL(frame_template, frame_context, macro="frame_footer", language=language)
    frame_context["header"] = tal.getTAL(frame_template, frame_context, macro="frame_header", language=language)

    html = tal.getTAL(frame_template, frame_context, macro="frame", language=language)
    return html
