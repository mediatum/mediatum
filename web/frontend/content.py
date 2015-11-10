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
import os
import urllib
from warnings import warn

from core import db, Node, File
from core.styles import getContentStyles, theme
from core.translation import lang, t
from contenttypes import Collections
from contenttypes.container import includetemplate, replaceModules
from web.frontend import Content
from utils.strings import ensure_unicode_returned
from utils.utils import getCollection, Link, getFormatedString
from utils.compat import iteritems
from web.frontend.searchresult import simple_search, extended_search, SearchResult
from core.systemtypes import Root
from contenttypes.container import Container
from mediatumtal import tal
from schema.schema import Metadatatype


logg = logging.getLogger(__name__)
q = db.query


def get_collections_node():
    return q(Collections).one()


class SingleFile(object):

    def __init__(self, file, link_params, language, fullstyle_name, words=None):
        node = file
        sys_filetypes = [unicode(x) for x in node.getSysFiles()]

        attachment = node.files.filter_by(filetype=u"attachment").first()
        if attachment is None:
            attachment = node.files.filter(~File.filetype.in_(sys_filetypes)).first()

        self.attachment = attachment
        self.datatype = node
        self.image = node.show_node_image()
        self.text = node.show_node_text(words, language=language)
        self.thumbnail = self.image
        if fullstyle_name:
            link_params["style"] = fullstyle_name
        self.link = u"/node?" + urllib.urlencode(link_params)
        self.shopping_bag_link = u'shoppingBag(\'{}\')'.format(node.id)
        self.node = node

    def getLink(self):
        warn("SingleFile.getLink() is deprecated, use SingleFile.link", DeprecationWarning)
        return self.link

    def getShoppingBagLink(self):
        warn("SingleFile.getShoppingBagLink() is deprecated, use SingleFile.shopping_bag_link", DeprecationWarning)
        return self.shopping_bag_link

    def getMetadata(self, separator=".", language=None):
        return self.node.show_node_text(separator=separator, language=language)

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
    if not "node.id" in sortfields:
        sortfields_to_comp["node.id"] = ("desc", node.id if node is not None else None)

    return sortfields_to_comp


def node_value_expression(name):
    if name == "node.id":
        return Node.id
    elif name == "node.orderpos":
        return Node.orderpos
    elif name == "node.name":
        return Node.name
    else:
        return getattr(Node.a, name)

comparisons = {
    "asc": (lambda l, r: l > r),
    "desc": (lambda l, r: l < r),
}

comparisons_inv = {
    "asc": comparisons["desc"],
    "desc": comparisons["asc"]
}


def make_cond(name_to_comp, invert=False):

    name, (op_name, val) = name_to_comp
    node_expr = node_value_expression(name)

    if val is None:
        if invert:
            return node_expr != None
        return

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
            eq_cond = expr == prev[1][1]
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

        # attributes can be NULL (means: attribute doesn't exists), so we must be careful about null ordering
        if not (sortfield.startswith("node.") or sortfield == "nodename"):
            if before:
                expr = expr.nullsfirst()
            else:
                expr = expr.nullslast()

        return query.order_by(expr)


SORT_FIELDS = 2
DEFAULT_FULL_STYLE_NAME = "full_standard"
DEFAULT_NODES_PER_PAGE = 9

class ContentList(Content):

    def __init__(self, node_query, collection, words=None):

        self.nodes_per_page = None
        self.nav_params = None
        self.before = None
        self.after = None
        self.lang = None
        self.words = words
        self.nodes = node_query
        self._num = -1
        self.content = None
        self.liststyle_name = None
        self.collection = collection
        self.sortfields = OrderedDict()
        self.default_fullstyle_name = None

        coll_default_full_style_name = collection.get("style_full")
        if coll_default_full_style_name is not None and coll_default_full_style_name != DEFAULT_FULL_STYLE_NAME:
            self.default_fullstyle_name = coll_default_full_style_name

    @property
    def files(self):
        warn("ContentList.files is deprecated, use ContentList.nodes", DeprecationWarning)
        return self.nodes

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
        if self.nodes_per_page:
            params["nodes_per_page"] = self.nodes_per_page

        if not ("before" in param_overrides or "after" in param_overrides):
            if self.before:
                params["before"] = self.before
            if self.after:
                params["after"] = self.after

        params.update(param_overrides)
        params = {k: v for k, v in iteritems(params) if v is not None}
        return u"?" + urllib.urlencode(params)

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
        return u"?id=" + str(self.content.id)

    def select_style_link(self, style):
        return self.nav_link(liststyle=style)

    def feedback(self, req):
        self.container_id = req.args.get("id")
        self.lang = lang(req)

        self.before = req.args.get("before", type=int)
        self.after = req.args.get("after", type=int)
        self.nodes_per_page = req.args.get("nodes_per_page", type=int)

        for i in range(SORT_FIELDS):
            key = "sortfield" + str(i)
            if key not in req.args:
                break
            sortfield = req.args[key].strip()
            if sortfield:
                self.sortfields[i] = req.args[key]

        if not self.sortfields:
            self.sortfields[0] = u"-node.id"

        self.liststyle_name = req.args.get("liststyle")

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

    def getContentStyles(self):
        if self.content.__class__ == ContentNode:
            return getContentStyles("bigview", contenttype=self.content.node.getContentType())
        else:
            return getContentStyles("smallview")  # , self.collection.get("style") or "default")


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
            show_node = q(Node).get(self.show_id)

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

        return ContentNode(show_node, 0, 0, self.words)

    def _page_nav_prev_next(self):
        q_nodes = self.nodes
        nodes_per_page = self.nodes_per_page or DEFAULT_NODES_PER_PAGE
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

        # get one more to find out if there are more nodes available

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
                q_additional_nodes = q_nodes.filter(position_cond)

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

        files = [SingleFile(n, dict(self.nav_params, show_id=n.id), self.lang, self.default_fullstyle_name) for n in nodes]

        page_nav = tal.getTAL(theme.getTemplate("content_nav.html"), ctx, macro="page_nav_prev_next", language=self.lang)
        return page_nav, files

    @ensure_unicode_returned(name="web.frontend.content.ContentList:html")
    def html(self, req):
        # do we want to show a single result or the result list?
        if self.content:
            # render single result
            headline = tal.getTAL(theme.getTemplate("content_nav.html"), {"nav": self}, macro="navheadline", language=self.lang)
            return headline + self.content.html(req)

        # render result list

        if self.liststyle_name:
            ls = self.liststyle_name
            # use default collection style
        else:
            ls = self.collection.get("style")
            if ls is None:
                # nothing found, use default style
                ls = "list"
            else:
                ls = ls.split(";")[0]

        liststyle = getContentStyles("smallview", ls, contenttype=u"")
        if not liststyle:
            raise Exception("invalid liststyle " + ls)
        liststyle = liststyle[0]

        ctx = {
            "page_nav": self.page_nav,
            "nav": self,
            "files": self.files,
            "sortfieldslist": self.getSortFieldsList(),
            "ids": ",".join(str(f.node.id) for f in self.files),
            "op": "", "query": req.args.get("query", "")}

        filesHTML = tal.getTAL(theme.getTemplate("content_nav.html"), ctx, macro="list_header", request=req)

        # use template of style and build html content
        ctx = {"files": self.files, "op": "", "language": self.lang}

        contentList = liststyle.renderTemplate(req, ctx)

        sidebar = u""  # check for sidebar
        if self.collection.get(u"system.sidebar") != "":
            for sb in [s for s in self.collection.get("system.sidebar").split(";") if s != ""]:
                l, fn = sb.split(":")
                if l == lang(req):
                    for f in [f for f in self.collection.getFiles() if fn.endswith(f.getName())]:
                        sidebar = replaceModules(self, req, includetemplate(self, f.retrieveFile(), {})).strip()
        if sidebar != "":
            return u'<div id="portal-column-one">{0}<div id="nodes">{1}</div>{0}</div><div id="portal-column-two">{2}</div>'.format(
                filesHTML,
                contentList,
                sidebar)
        else:
            return u'{0}<div id="nodes">{1}</div>{0}'.format(filesHTML, contentList)

# paths


def getPaths(node):
    res = []

    def r(node, path):
        if isinstance(node, Root):
            return
        for p in node.getParents():
            path.append(p)
            if not isinstance(p, Collections):
                r(p, path)
        return path

    paths = []

    p = r(node, [])
    omit = 0
    if p:
        for node in p:
            if node.has_read_access():
                if node.type in ("directory", "home", "collection") or node.type.startswith("directory"):
                    paths.append(node)
                if isinstance(node, (Collections, Root)):
                    paths.reverse()
                    if len(paths) > 0 and not omit:
                        res.append(paths)
                    omit = 0
                    paths = []
            else:
                omit = 1
    if len(res) > 0:
        return res
    else:
        return []


class ContentNode(Content):

    def __init__(self, node, nr=0, num=0, words=None):
        self.node = node
        self.id = node.id
        self.paths = []
        self.nr = nr
        self.num = num
        self.words = words
        self.full_style_name = None

    def feedback(self, req):
        self.full_style_name = req.args.get("style")

    def getContentStyles(self):
        return getContentStyles("bigview", contenttype=self.node.type)

    def actual(self):
        return "(%d/%d)" % (int(self.nr) + 1, self.num)

    def select_style_link(self, style):
        params = {"id": self.id, "style": style}
        return u"node?" + urllib.urlencode(params)

    @ensure_unicode_returned(name="web.frontend.content:html")
    def html(self, req):
        language = lang(req)
        paths = u""
        # XXX: remove session-stored Node instances!
        self.node = db.refresh(self.node)
        show_node_big = ensure_unicode_returned(self.node.show_node_big, name="show_node_big of %s" % self.node)

        if not isinstance(self.node, Container):
            plist = getPaths(self.node)
            paths = tal.getTAL(theme.getTemplate("content_nav.html"), {"paths": plist}, macro="paths", language=language)

        full_styles = getContentStyles("bigview", self.full_style_name or DEFAULT_FULL_STYLE_NAME, contenttype=self.node.type)

        if full_styles:
            return getFormatedString(show_node_big(req, template=full_styles[0].getTemplate())) + paths
        else:
            return getFormatedString(show_node_big(req)) + paths


def fileIsNotEmpty(file):
    with open(file) as f:
        s = f.read().strip()
    if s:
        return 1
    else:
        return 0


def mkContentNode(req):
    id = req.args.get("id", get_collections_node().id)
    node = q(Node).get(id)

    if node is None:
        return ContentError("No such node", 404)
    if not node.has_read_access():
        return ContentError("Permission denied", 403)

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
            c = ContentList(allowed_nodes, getCollection(node))
            c.feedback(req)
            c.node = node
            return c

    version_id = req.args.get("v")
    version = node.get_tagged_version(unicode(version_id))

    c = ContentNode(version) if version is not None else ContentNode(node)
    c.feedback(req)
    return c


class ContentError(Content):

    def __init__(self, error, status):
        self.error = error
        self._status = status

    @ensure_unicode_returned(name="contenterror.html")
    def html(self, req):
        return tal.getTAL(theme.getTemplate("content_error.html"), {"error": self.error}, language=lang(req))

    def getContentStyles(self):
        return []

    def status(self):
        return self._status


class ContentArea(Content):

    def __init__(self):
        self._content = None
        self.collection = None
        self.collectionlogo = None
        self.params = ""

    @property
    def content(self):
        if self._content is None:
            self._content = ContentNode(get_collections_node())
        return self._content

    @content.setter
    def content(self, content):
        self._content = content

    def getPath(self, language=None, check_access=False):
        path = []
        if hasattr(self.content, "node"):
            cd = self.content.node
            if cd is not None:
                if isinstance(cd, Container):
                    path.append(Link('', cd.getLabel(language), ''))
                else:
                    path.append(Link('', cd.getLabel(), ''))
                while True:
                    parents = cd.parents
                    if check_access:
                        parents = list(cd.parents.filter_read_access())
                    else:
                        parents = list(cd.parents)
                    if len(parents) == 0:
                        break
                    cd = parents[0]
                    if cd is q(Collections).one() or cd is q(Root).one():
                        break
                    if isinstance(cd, Container):
                        path.append(Link('/?id={id}&dir={id}'.format(id=cd.id), cd.getLabel(language), cd.getLabel(language)))
                    else:
                        path.append(Link('/?id={id}&dir={id}'.format(id=cd.id), cd.getLabel(), cd.getLabel()))
        elif hasattr(self.content, "linkname") and hasattr(self.content, "linktarget"):
            path.append(Link(self.content.linktarget, self.content.linkname, self.content.linkname))
        path.reverse()
        return path

    def feedback(self, req):
        content = None
        if req.args.get("query", "").strip():
            content = simple_search(req)
        elif req.args.get("query1", "").strip():
            content = extended_search(req)

        if content is None:
            self.content = mkContentNode(req)
        else:
            self.content = content

        if hasattr(self.content, "collection"):
            self.collection = self.content.collection
            if self.collection:
                self.collectionlogo = CollectionLogo(self.collection)

        if hasattr(self.content, "getParams"):
            self.params = '&' + self.content.getParams()

    def actNode(self):
        if hasattr(self.content, 'node'):
            return self.content.node
        else:
            return None

    @ensure_unicode_returned
    def html(self, req):
        if "raw" in req.args:
            path = ""
        else:
            if hasattr(self.content, "node"):
                node = self.content.node
            else:
                node = None

            if node is None:
                printlink = '/print/0'
            else:
                if isinstance(node, Container) and node.get("system.print") == "1":
                    printlink = '/print/' + unicode(node.id)
                else:
                    printlink = None

            if printlink and "sortfield0" in req.args:
                printlink += '?sortfield0=' + req.args.get("sortfield0") + '&sortfield1=' + req.args.get("sortfield1")

            if req.args.get("show_navbar") == 0 or req.session.get("area") == "publish":
                breadcrumbs = []
            else:
                try:
                    breadcrumbs = self.getPath(lang(req), check_access=True)
                except AttributeError:
                    logg.exception("exception in html")
                    return req.error(404, "Object cannot be shown")

            styles = self.content.getContentStyles()

            path = tal.getTAL(theme.getTemplate("content_nav.html"),
                              {"params": self.params,
                               "path": breadcrumbs,
                               "styles": styles,
                               "logo": self.collectionlogo,
                               "select_style_link": self.content.select_style_link,
                               "id": id,
                               "nodeprint": "1" if printlink else "0",  # XXX: template compat for non-default templates
                               "printlink": printlink,
                               "area": req.session.get("area", "")},
                              macro="path",
                              request=req)

        return path + '\n<!-- CONTENT START -->\n' + self.content.html(req) + '\n<!-- CONTENT END -->\n'

    def status(self):
        return self.content.status()


class CollectionLogo(Content):

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


def getContentArea(req):
    return ContentArea()
