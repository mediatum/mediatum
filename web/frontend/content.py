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
from collections import OrderedDict
import logging
from warnings import warn

from core import db, config, Node, File, webconfig, styles
from core.styles import get_list_style, get_styles_for_contenttype
from core.translation import lang, t
from core.webconfig import node_url
from contenttypes import Content
from contenttypes.container import includetemplate
from utils.strings import ensure_unicode_returned
from utils.utils import getFormatedString
from utils.compat import iteritems
from web.frontend.search import simple_search, extended_search
from contenttypes.container import Container
from mediatumtal import tal
from schema.schema import Metadatatype
from core.database.postgres import mediatumfunc
from sqlalchemy_continuum.utils import version_class
import json
from utils.pathutils import get_accessible_paths
from web.frontend.contentbase import ContentBase


logg = logging.getLogger(__name__)
q = db.query


class SingleFile(object):

    def __init__(self, file, link_params, language, fullstyle_name, separator=None):
        node = file
        sys_filetypes = [unicode(x) for x in node.get_sys_filetypes()]

        attachment = node.files.filter_by(filetype=u"attachment").first()
        if attachment is None:
            attachment = node.files.filter(~File.filetype.in_(sys_filetypes)).first()

        self.attachment = attachment
        self.datatype = node
        self.image = node.show_node_image()
        self.text = node.show_node_text(separator=separator, language=language)
        self.thumbnail = self.image
        if fullstyle_name:
            link_params["style"] = fullstyle_name
        self.link = node_url(**link_params)
        self.shopping_bag_link = u'shoppingBag(\'{}\')'.format(node.id)
        self.node = node

    def getLink(self):
        warn("SingleFile.getLink() is deprecated, use SingleFile.link", DeprecationWarning)
        return self.link

    @property
    def file(self):
        warn("SingleFile.file is deprecated, use SingleFile.node", DeprecationWarning)
        return self.node


def prepare_sortfields(node, pos_to_sortfield):
    sortfields_to_comp = OrderedDict()
    sortfields = pos_to_sortfield.values()

    for sortfield in sortfields:
        if sortfield[0] == "-":
            order = "desc"
            sortfield = sortfield[1:]
        else:
            order = "asc"

        if node is None:
            value = None
        else:
            value = node.get_special(sortfield, default=None)

        sortfields_to_comp[sortfield] = (order, value)

    # sort position must always be unique. That means that the node id must be part of the position key.
    if not ("node.id" in sortfields or "-node.id" in sortfields):
        sortfields_to_comp["node.id"] = ("desc", node.id if node is not None else None)

    return sortfields_to_comp


def node_value_expression(name):
    if name == "node.id":
        return Node.id
    elif name == "node.orderpos":
        return Node.orderpos
    elif name == "node.name" or name == "nodename":
        return Node.name
    else:
        return mediatumfunc.jsonb_limit_to_size(Node.attrs[name])

comparisons = {
    "asc": (lambda l, r: l > r),
    "desc": (lambda l, r: l < r),
}

comparisons_inv = {
    "asc": comparisons["desc"],
    "desc": comparisons["asc"]
}


def _limit_to_size(val, size=2000):
    """This should do the same as the SQL function jsonb_limit_to_size"""
    if isinstance(val, basestring):
        return val[:size]
    else:
        return val


def _prepare_value(name, val):
    if val is None:
        return val
    
    val = _limit_to_size(val)
    # XXX: that's a bit hacky, find a better solution (maybe in node_value_expression?)
    if name not in ("node.id", "node.orderpos", "node.name"):
        return json.dumps(val)
    else:
        return val


def make_cond(name_to_comp, invert=False):

    name, (op_name, val) = name_to_comp
    node_expr = node_value_expression(name)

    if val is None:
        if invert:
            return node_expr != None
        return

    val = _prepare_value(name, val)

    if invert:
        return comparisons_inv[op_name](node_expr, val)
    else:
        return comparisons[op_name](node_expr, val) | (node_expr == None)


def position_filter(sortfields_to_comp, after=False, before=False):

    assert before or after

    iter_sortfield = iteritems(sortfields_to_comp)
    prev_sortfields_to_comp = []

    first_sortfield = next(iter_sortfield)
    cond = make_cond(first_sortfield, invert=before)
    prev_sortfields_to_comp.append(first_sortfield)

    # add remaining sortfields if present
    for sortfield_to_comp in iter_sortfield:
        # We are doing a "tuple" comparision here. If the first field is equivalent, we have to compare the seconds field and so on.
        # first add comparison for current field...
        sub_cond = make_cond(sortfield_to_comp, invert=before)
        # ... and add equivalence conditions for previous fields
        for prev in prev_sortfields_to_comp:
            expr = node_value_expression(prev[0])
            # XXX: can we replace this by make_cond or something like that?
            eq_cond = expr == _prepare_value(prev[0][0], prev[1][1])
            sub_cond &= eq_cond

        prev_sortfields_to_comp.append(sortfield_to_comp)

        # or-append condition for current field to full condition
        if cond is None:
            cond = sub_cond
        else:
            cond |= sub_cond

    return cond


def apply_order_by_for_sortfields(query, sortfields_to_comp, before=False):
    for sortfield, (order, _) in iteritems(sortfields_to_comp):
        if order == "desc":
            desc = not bool(before)
        else:
            desc = bool(before)

        expr = node_value_expression(sortfield)

        if desc:
            expr = expr.desc()

        # attributes can be NULL (means: attribute doesn't exist), so we must be careful about null ordering
        if not (sortfield.startswith("node.") or sortfield == "nodename"):
            if before:
                expr = expr.nullsfirst()
            else:
                expr = expr.nullslast()

        query = query.order_by(expr)

    return query


def get_accessible_node(nid):
    """Fetches node by ID, checking read access.
    Returns a Node or Node if node not found or not accessible by user."""
    return q(Node).filter_by(id=nid).filter_read_access().prefetch_attrs().prefetch_system_attrs().scalar()
    

SORT_FIELDS = 2
DEFAULT_FULL_STYLE_NAME = "full_standard"


class ContentList(ContentBase):

    def __init__(self, node_query, container, paths, words=None, show_sidebar=True):

        self.nodes = node_query
        self.container = container
        self.paths = paths
        self.words = words
        self.show_sidebar = show_sidebar
        self.nodes_per_page = None
        self.nav_params = None
        self.before = None
        self.after = None
        self.lang = None
        self._num = -1
        self.content = None
        self.liststyle_name = None
        self.collection = container.get_collection()
        self.sortfields = OrderedDict()
        self.default_fullstyle_name = None

        coll_default_full_style_name = self.collection.get("style_full")
        if coll_default_full_style_name is not None and coll_default_full_style_name != DEFAULT_FULL_STYLE_NAME:
            self.default_fullstyle_name = coll_default_full_style_name

    @property
    def node(self):
        return self.container

    @property
    def logo(self):
        return CollectionLogo(self.collection)

    @property
    def has_elements(self):
        if self._num > 0:
            return True
        return self.nodes.first() is not None

    @property
    def num(self):
        if self._num == -1:
            self._num = self.nodes.count()
        return self._num

    def length(self):
        return self.num

    def nav_link(self, **param_overrides):
        """
        params can be removed from the URL by setting them to None in param_overrides
        """
        params = self.nav_params.copy()
        if self.liststyle_name:
            params["liststyle"] = self.liststyle_name
        if self.nodes_per_page_from_req:
            params["nodes_per_page"] = self.nodes_per_page_from_req

        if not ("before" in param_overrides or "after" in param_overrides):
            if self.before:
                params["before"] = self.before
            if self.after:
                params["after"] = self.after

        params.update(param_overrides)
        params = {k: v for k, v in iteritems(params) if v is not None}
        return node_url(**params)

    def link_first(self):
        return self.nav_link(show_id=None, result_nav="first")

    def link_last(self):
        return self.nav_link(show_id=None, result_nav="last")

    def link_next(self):
        # replace show_id because it can be changed in self.feedback()
        return self.nav_link(show_id=self.show_id, result_nav="next")

    def link_prev(self):
        # replace show_id because it can be changed in self.feedback()
        return self.nav_link(show_id=self.show_id, result_nav="prev")

    def link_back(self):
        # remove navigation params, go back to list view
        return self.nav_link(show_id=None, result_nav=None)

    def link_current_node(self):
        return node_url(self.content.id)

    def select_style_link(self, style):
        # self.content means: we're showing a single result node.
        # Therefore, we want to change the style of the node, not the list.
        if self.content is not None:
            return self.nav_link(style=style)

        return self.nav_link(liststyle=style)

    def feedback(self, req):
        self.container_id = req.args.get("id", type=int)
        self.lang = lang(req)

        self.before = req.args.get("before", type=int)
        self.after = req.args.get("after", type=int)

        for i in range(SORT_FIELDS):
            key = "sortfield" + str(i)
            if key not in req.args:
                break
            sortfield = req.args[key].strip()
            if sortfield:
                self.sortfields[i] = req.args[key]

        if not self.sortfields:
            default_sortfield = self.collection.get(u"sortfield")
            self.sortfields[0] = default_sortfield if default_sortfield else u"-node.id"

        liststyle_name = req.args.get("liststyle")

        if liststyle_name:
            ls = liststyle_name
            # use default collection style
        else:
            ls = self.collection.get("style", None)
            if ls is None:
                # nothing found, use default style
                ls = "list"
            else:
                ls = ls.split(";")[0]

        liststyle = get_list_style(ls)
        
        if not liststyle:
            raise Exception("invalid liststyle '" + ls + "'")
        
        self.liststyle = liststyle

        self.nodes_per_page_from_req = req.args.get("nodes_per_page", type=int)
        
        if self.nodes_per_page_from_req:
            self.nodes_per_page = self.nodes_per_page_from_req
        else:
            self.nodes_per_page = liststyle.nodes_per_page
        
        self.nav_params = {k: v for k, v in req.args.items()
                           if k not in ("before", "after", "style", "sortfield", "page", "nodes_per_page")}

        self.show_id = req.args.get("show_id")
        self.result_nav = req.args.get("result_nav")

        if self.show_id or self.result_nav:
            # single result view
            self.content = self._single_result()
            return self.content.feedback(req)
        else:
            # prepare content list page navigation
            self.page_nav, self.files = self._page_nav_prev_next()

    def getSortFieldsList(self):

        class SortChoice(object):

            def __init__(self, label, value, descending, selected):
                self.label = label
                self.value = value
                self.descending = descending
                self.isselected = self.value == selected

            def getLabel(self):
                return self.label

            def getName(self):
                return self.value

            def selected(self):
                if self.isselected:
                    return "selected"
                else:
                    return None
        l = []
        ok = 0

        try:
            first_node = self.nodes[0]
        except IndexError:
            return []

        sort_metafields = first_node.metadatatype.metafields.filter(Metadatatype.a.opts.like("%o%"))

        for i in range(SORT_FIELDS):
            sort_choice = []
            sortfield = self.sortfields.get(i)

            if not sortfield:
                sort_choice += [SortChoice("", "", 0, "")]
            else:
                sort_choice += [SortChoice("", "", 0, "not selected")]

            for field in sort_metafields:
                sort_choice += [SortChoice(field.label, field.name, 0, sortfield)]
                sort_choice += [SortChoice(field.label + t(self.lang, "descending"), "-" + field.name, 1, sortfield)]

            if len(sort_choice) < 2:
                # no choice for the user
                return []

            l += [sort_choice]

        return l

    @property
    def content_styles(self):
        if isinstance(self.content, ContentNode):
            return get_styles_for_contenttype(self.content.node.type)
        else:
            return styles.list_styles.values()


    def _single_result(self):
        # 5 cases (show_id, nav):
        # (None, "first") => show first node in result
        # (None, "last") => show last node in result
        # (<id>, "next") => go to next node in result relative to <id>
        # (<id>, "prev") => go to previous node in result relative to <id>
        # (<id>, None) => show node <id> in result list (*)

        # * (no check if node is in list, but doesn't really matter, I think)

        if self.show_id:
            # show_id needed for all cases except first and last
            show_node = get_accessible_node(self.show_id)
            
            if show_node is None:
                return NodeNotAccessible()

        nav = self.result_nav

        if nav:
            if nav in ("next", "prev"):
                # we want to display the node _after_ or _before_ `show_node`
                sortfields_to_comp = prepare_sortfields(show_node, self.sortfields)
                before = nav == "prev"
                position_cond = position_filter(sortfields_to_comp, after=nav=="next", before=before)
                q_nodes = self.nodes.filter(position_cond)
                q_nodes = apply_order_by_for_sortfields(q_nodes, sortfields_to_comp, before=before)

            elif nav in ("first", "last"):
                sortfields_to_comp = prepare_sortfields(None, self.sortfields)
                q_nodes = apply_order_by_for_sortfields(self.nodes, sortfields_to_comp, before=nav=="last")

            # replace show_node with our navigation result if something was found. Else, just display the old node.
            new_node = q_nodes.first()
            if new_node:
                show_node = new_node
                self.show_id = show_node.id

        else:
            # doing nothing here when `nav` was not given
            pass

        return ContentNode(show_node, self.paths, 0, 0, self.words)

    def _page_nav_prev_next(self):
        q_nodes = self.nodes
        nodes_per_page = self.nodes_per_page
        # self.after set <=> moving to next page
        # self.before set <=> moving to previous page
        # nothing set <=> first page

        if self.after or self.before:
            comp_node = q(Node).get(self.after or self.before)
            sortfields_to_comp = prepare_sortfields(comp_node, self.sortfields)
            position_cond = position_filter(sortfields_to_comp, self.after, self.before)
            q_nodes = q_nodes.filter(position_cond)
        else:
            # first page
            sortfields_to_comp = prepare_sortfields(None, self.sortfields)

        q_nodes = apply_order_by_for_sortfields(q_nodes, sortfields_to_comp, self.before)
        

        ctx = {
            "nav": self,
            "before": None,
            "after": None
        }

        # we fetch one more to see if more nodes are available (on the next page)
        nodes = q_nodes.limit(nodes_per_page+1).prefetch_attrs().all()

        # Check if we got enough nodes and try to load more if needed.
        # Maybe there were enough results for the database LIMIT, but SQLAlchemy filtered out some duplicates.
        node_count = len(nodes)
        # It doesn't make sense to try again if no results were returned. Empty container is empty...
        if node_count:
            while node_count <= nodes_per_page:
                refetch_limit = nodes_per_page - node_count + 1
                sortfields_to_comp = prepare_sortfields(nodes[-1], self.sortfields)
                position_cond = position_filter(sortfields_to_comp, self.after or not self.before, self.before)
                q_additional_nodes = self.nodes.filter(position_cond)
                q_additional_nodes = apply_order_by_for_sortfields(q_additional_nodes, sortfields_to_comp, self.before)

                additional_nodes = q_additional_nodes.limit(refetch_limit).prefetch_attrs().all()
                if not additional_nodes:
                    # no more nodes found (first or last page), stop trying
                    break
                nodes += additional_nodes
                node_count += len(additional_nodes)

        if len(nodes) > nodes_per_page:
            # more nodes available when navigating in the same direction
            # last node will be displayed on next page, remove it
            nodes = nodes[:-1]
            if self.before:
                ctx["before"] = nodes[-1].id
            else:
                ctx["after"] = nodes[-1].id

        if self.before:
            # going backwards, so it must be possible to go forward in the next step
            ctx["after"] = nodes[0].id
        elif self.after:
            # going forward, so it must be possible to go back in the next step
            ctx["before"] = nodes[0].id

        if self.before:
            # going backwards inverts the order, invert again for display
            nodes = nodes[::-1]

        files = []
        for n in nodes:
            nav_params = dict(self.nav_params, show_id=n.id)
            # special case: no id set <=> we are on the collections root node
            if "id" not in nav_params:
                nav_params["id"] = self.collection.id

            sfile = SingleFile(n, nav_params, self.lang, self.default_fullstyle_name, self.liststyle.maskfield_separator)
            files.append(sfile)

        page_nav = tal.getTAL(webconfig.theme.getTemplate("content_nav.html"), ctx, macro="page_nav_prev_next", language=self.lang)
        return page_nav, files

    @ensure_unicode_returned(name="web.frontend.content.ContentList:html")
    def html(self, req):
        # do we want to show a single result or the result list?
        if self.content:
            # render single result
            headline = tal.getTAL(webconfig.theme.getTemplate("content_nav.html"), {"nav": self}, macro="navheadline", language=self.lang)

            return headline + self.content.html(req)

        # render result list

        ctx = {
            "page_nav": self.page_nav,
            "nav": self,
            "files": self.files,
            "sortfieldslist": self.getSortFieldsList(),
            "ids": ",".join(str(f.node.id) for f in self.files),
            "op": "", "query": req.args.get("query", "")}

        filesHTML = tal.getTAL(webconfig.theme.getTemplate("content_nav.html"), ctx, macro="list_header", request=req)

        # use template of style and build html content
        ctx = {"files": self.files, "op": "", "language": self.lang}

        contentList = self.liststyle.render_template(req, ctx)

        if self.show_sidebar:
            sidebar = u""  # check for sidebar
            if self.collection.get(u"system.sidebar") != "":
                for sb in [s for s in self.collection.get("system.sidebar").split(";") if s != ""]:
                    l, fn = sb.split(":")
                    if l == lang(req):
                        for f in [f for f in self.collection.getFiles() if fn.endswith(f.getName())]:
                            sidebar = includetemplate(self, f.retrieveFile(), {}).strip()
            if sidebar:
                return u'<div id="portal-column-one">{0}<div id="nodes">{1}</div>{0}</div><div id="portal-column-two">{2}</div>'.format(
                    filesHTML,
                    contentList,
                    sidebar)

        return u'{0}<div id="nodes">{1}</div>{0}'.format(filesHTML, contentList)


class ContentNode(ContentBase):

    def __init__(self, node, paths=None, nr=0, num=0, words=None):
        self._node = node
        self.collection = node.get_collection()
        self.id = node.id
        self.paths = paths
        self.nr = nr
        self.num = num
        self.words = words
        self.full_style_name = None

    def feedback(self, req):
        self.full_style_name = req.args.get("style")

    @property
    def cache_duration(self):
        return self.node.cache_duration

    @property
    def node(self):
        return self._node

    @property
    def logo(self):
        return CollectionLogo(self.collection)

    @property
    def content_styles(self):
        return get_styles_for_contenttype(self._node.type)

    def select_style_link(self, style):
        version = self._node.tag if isinstance(self._node, version_class(Node)) else None
        return node_url(self.id, version=version, style=style)

    @ensure_unicode_returned(name="web.frontend.content:html")
    def html(self, req):
        show_node_big = ensure_unicode_returned(self._node.show_node_big, name="show_node_big of %s" % self._node)
        style_name = self.full_style_name or DEFAULT_FULL_STYLE_NAME
        node_html = getFormatedString(show_node_big(req, style_name))
        
        if self.paths:
            occurences_html = render_content_occurences(self.node, req, self.paths)
        else:
            occurences_html = u""

        return node_html + occurences_html


class NodeNotAccessible(ContentBase):

    def __init__(self, error="no such node", status=404):
        self.error = error
        self.status = status
        
    @property
    def cache_duration(self):
        return 30
    

def make_node_content(node, req, paths):
    """Renders the inner parts of the content area.
    The current node can be a container or a content node. 
    A container can render a static HTML page, a node list view or a single node from that list.
    For a content node, the detail view is displayed.
    If the wanted node cannot be accessed, a NodeNotAccessible instance is returned.
    """
    if node is None:
        return NodeNotAccessible()

    if isinstance(node, Container):
        # try to find a start page
        if "files" not in req.args and len(filter(None, node.getStartpageDict().values())) > 0:
            # XXX: would be better to show an error message for missing, but configured start pages
            html_files = node.files.filter_by(filetype=u"content", mimetype=u"text/html")
            for f in html_files:
                if f.exists and f.size > 0:
                    return ContentNode(node)

        if node.show_list_view:
            # no startpage found, list view requested
            allowed_nodes = node.content_children_for_all_subcontainers_with_duplicates.filter_read_access()
            c = ContentList(allowed_nodes, node, paths)
            c.feedback(req)
            # if ContentList feedback produced a content error, return that instead of the list itself
            if isinstance(c.content, NodeNotAccessible):
                return c.content
            return c

    
    version_id = req.args.get("v")
    
    if version_id:
        version = node.get_tagged_version(unicode(version_id))
    else:
        version = None

    c = ContentNode(version, paths) if version is not None else ContentNode(node, paths)
    c.feedback(req)
    return c


def make_content_nav_printlink(req, node):
    printlink = None
    if isinstance(node, Container) and config.getboolean("config.enable_printing") and node.system_attrs.get("print", "1") == "1":
        # printing is allowed for containers by default, unless system.print != "1" is set on the node
        printlink = '/print/' + unicode(node.id)

    if printlink and "sortfield0" in req.args:
        printlink += '?sortfield0=' + req.args.get("sortfield0") + '&sortfield1=' + req.args.get("sortfield1")

    return printlink
    

def render_content_nav(req, node, logo, styles, select_style_link, paths):
    if paths:
        shortest_path = sorted(paths, key=lambda p: (len(p), p[-1].id))[0]
    else:
        shortest_path = None   
    
    content_nav_html = tal.getTAL(webconfig.theme.getTemplate("content_nav.html"),
                      {"path": shortest_path,
                       "styles": styles,
                       "logo": logo,
                       "select_style_link": select_style_link,
                       "node": node,
                       "printlink": make_content_nav_printlink(req, node)},
                      macro="content_nav",
                      request=req)

    return content_nav_html


def get_make_search_content_function(req):
    """Derives from query parameters if a simple or extended search should be run.
    Returns the function that renders the search content or None, if no search should be done.
    """
        
    if req.args.get("query", "").strip():
        return simple_search
    else:
        searchmode = req.args.get("searchmode")

        if searchmode in ("extended", "extendedsuper"):
            if searchmode == "extended":
                field_range = xrange(1,4)
            elif searchmode == "extendedsuper":
                field_range = xrange(1,11)

            for ii in field_range:
                if req.args.get("query" + str(ii), "").strip():
                    return extended_search


def render_content_error(error, language):
    return tal.getTAL(webconfig.theme.getTemplate("content_error.html"), {"error": error}, language=language)


def render_content_occurences(node, req, paths):
    language = lang(req)
    return tal.getTAL(webconfig.theme.getTemplate("content_nav.html"), {"paths": paths}, macro="paths", language=language)


def render_content(node, req, render_paths=True):
    make_search_content = get_make_search_content_function(req)

    if render_paths and node is not None:
        paths = get_accessible_paths(node, q(Node).prefetch_attrs())
    else:
        paths = None

    if make_search_content is None:
        content_or_error = make_node_content(node, req, paths)
    else:
        content_or_error = make_search_content(req, paths)

    
    cache_duration = content_or_error.cache_duration
    if cache_duration:
        req.reply_headers["Cache-Control"] = "max-age=" + str(cache_duration)
    else:
        req.reply_headers["Cache-Control"] = "no-cache"

    if isinstance(content_or_error, NodeNotAccessible):
        req.setStatus(content_or_error.status)
        return render_content_error(content_or_error.error, lang(req))

    content = content_or_error
    
    if "raw" in req.args:
        content_nav_html = ""
    else:
        node = content.node
        logo = content.logo
        select_style_link = content.select_style_link
        styles = content.content_styles
        content_nav_html = render_content_nav(req, node, logo, styles, select_style_link, paths)


    content_html = content_nav_html + "\n" + content.html(req)
    return content_html


class CollectionLogo(object):

    def __init__(self, collection):
        self.collection = collection
        self.path = collection.getLogoPath()
        self.url = collection.get("url")
        self.show_on_html = collection.get("showonhtml")

        if self.path != "":
            self.path = '/file/' + unicode(self.collection.id) + '/' + self.path

    def getPath(self):
        return self.path

    def getURL(self):
        return self.url

    def getShowOnHTML(self):
        return self.show_on_html
