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
from web.frontend.searchresult import simple_search, extended_search
from core.systemtypes import Root
from contenttypes.container import Container
from mediatumtal import tal


logg = logging.getLogger(__name__)
q = db.query


def get_collections_node():
    return q(Collections).one()


class SingleFile(object):

    def __init__(self, file, nr, num, words=None, language=None, fullstyle_name=None):
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
        link_params = {"id": node.id}
        if fullstyle_name:
            link_params["style"] = fullstyle_name
        self.link = u"/node?" + urllib.urlencode(link_params)
        self.shopping_bag_link = u'shoppingBag(\'{}\')'.format(node.id)
        self.node = node
        self.nr = nr
        self.num = num

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


SORT_FIELDS = 0

DEFAULT_FULL_STYLE_NAME = "full_standard"

class ContentList(Content):

    def __init__(self, node_query, collection, words=None):

        self.nr = -1
        self.page = 0
        self.nodes_per_page = None
        self.nav_params = {}
        self.before = None
        self.after = None
        self.lang = "en"
        self.words = words
        self.nodes = node_query
        self._num = -1
        self.content = None
        self.id2pos = {}
        self.liststyle_name = None
        self.collection = collection
        self.sortfields = []
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

    def actual(self):
        return "(%d/%d)" % (int(self.nr) + 1, self.num)

    def in_list(self, id):
        return id in self.id2pos

    def link_first(self):
        self.id2pos[self.nodes[0].id] = 0
        return "/node?id=" + unicode(self.nodes[0].id)

    def link_last(self):
        self.id2pos[self.nodes[self.num - 1].id] = self.num - 1
        return "/node?id=" + unicode(self.nodes[self.num - 1].id)

    def link_prev(self):
        if self.nr > 0:
            self.id2pos[self.nodes[self.nr - 1].id] = self.nr - 1
            return "/node?id=" + unicode(self.nodes[self.nr - 1].id)
        else:
            return self.link_first()

    def link_next(self):
        if self.nr < self.num - 1:
            self.id2pos[self.nodes[self.nr + 1].id] = self.nr + 1
            return "/node?id=" + unicode(self.nodes[self.nr + 1].id)
        else:
            return self.link_last()

    def link_back(self):
        return "node?back=y"

    def nav_link(self, **param_overrides):
        params = {"id": self.container_id}
        if self.liststyle_name:
            params["style"] = self.liststyle_name
        if self.nodes_per_page:
            params["nodes_per_page"] = self.nodes_per_page

        if not ("before" in param_overrides or "after" in param_overrides):
            if self.before:
                params["before"] = self.before
            if self.after:
                params["after"] = self.after

        params.update(param_overrides)
        return u"?" + urllib.urlencode(params)

    def select_style_link(self, style):
        return self.nav_link(style=style)

    def nav_link_before(self):
        return self.nav_link(before=self.next_before)

    def nav_link_after(self):
        return self.nav_link(after=self.next_after)

    def feedback(self, req):
        container_id = req.args.get("id")
        if container_id:
            try:
                self.nr = self.id2pos[container_id]
            except KeyError:
                pass  # happens for first node (the directory)

        self.container_id = container_id
        self.lang = lang(req)

        if "page" in req.args:
            self.page = req.args.get("page", type=int)
            self.nr = -1

        if "before" in req.args or "after" in req.args:
            self.page = -1

        self.before = req.args.get("before", type=int)
        self.after = req.args.get("after", type=int)
        self.nodes_per_page = req.args.get("nodes_per_page", type=int)

        if "back" in req.args:
            self.nr = -1

        for i in range(SORT_FIELDS):
            if ("sortfield%d" % i) in req.args:
                self.sortfields[i] = req.args["sortfield%d" % i]

        # XXX: would be very slow to do this here, ideas?
#         self.nodes.sort_by_fields(self.sortfields)

        self.content = None
        if self.nr >= 0 and self.nr < self.num:
            self.content = ContentNode(self.nodes[self.nr], self.nr, self.num, self.words)

        self.liststyle_name = req.args.get("style")

        if self.content:
            return self.content.feedback(req)

    def getSortFieldsList(self):
        class SortChoice:

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
        for i in range(SORT_FIELDS):
            sortfields = []
            if self.num:
                if not self.sortfields[i]:
                    sortfields += [SortChoice("", "", 0, "")]
                else:
                    sortfields += [SortChoice("", "", 0, "not selected")]
                for field in self.nodes[0].getMetaFields():
                    if "o" in field.getOption():
                        sortfields += [SortChoice(field.getLabel(), field.getName(), 0, self.sortfields[i])]
                        sortfields += [SortChoice(field.getLabel() + t(self.lang, "descending"),
                                                  "-" + field.getName(), 1, self.sortfields[i])]
            l += [sortfields]
            if len(sortfields) > 1:
                ok = 1
        if not ok:
            return []
        else:
            return l

    def getContentStyles(self):
        if self.content.__class__ == ContentNode:
            return getContentStyles("bigview", contenttype=self.content.node.getContentType())
        else:
            return getContentStyles("smallview")  # , self.collection.get("style") or "default")

    def _page_nav_numbers(self, nodes_per_page, language, req):
        nav_list = []
        nav_page = []
        files = []

        min = 0
        max = (self.num + nodes_per_page - 1) / nodes_per_page - 1
        left = self.page - 6
        right = self.page + 6

        if left < 0:
            left = 0
        if right > max or right >= max - 2:
            right = max
        if left <= min + 2:
            left = min

        if left > min:
            nav_list.append("/node?page=" + unicode(min))
            nav_list.append('...')
            nav_page.append(min)
            nav_page.append(-1)

        for a in range(left, right + 1):
            nav_list.append("/node?page=" + unicode(a))
            nav_page.append(a)

        if right < max:
            nav_list.append('...')
            nav_list.append("/node?page=" + unicode(max))
            nav_page.append(-1)
            nav_page.append(max)

        displayed_nodes = self.nodes.offset(self.page * nodes_per_page).limit(nodes_per_page).all()
        for pos, node in enumerate(displayed_nodes):
            self.id2pos[node.id] = pos
            files.append(SingleFile(node, pos, self.num, language=language))

        ctx = {
            "nav_list": nav_list, "nav_page": nav_page, "act_page": self.page
        }

        page_nav = tal.getTAL(theme.getTemplate("content_nav.html"), ctx, macro="page_nav_numbers", language=language)
        return page_nav, files

    def _page_nav_prev_next(self, nodes_per_page, language, req):
        q_nodes = self.nodes

        # self.after set <=> moving to next page
        # self.before set <=> moving to previous page
        # nothing set <=> first page

        if self.after:
            q_nodes = q_nodes.filter(Node.id < self.after)

        elif self.before:
            q_nodes = q_nodes.filter(Node.id > self.before)

        if self.before:
            q_nodes = q_nodes.order_by(Node.id)
        else:
            q_nodes = q_nodes.order_by(Node.id.desc())

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
                if self.before:
                    q_additional_nodes = q_nodes.filter(Node.id > nodes[-1].id)
                else:
                    q_additional_nodes = q_nodes.filter(Node.id < nodes[-1].id)

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

        files = [SingleFile(n, 0, 0, language=language, fullstyle_name=self.default_fullstyle_name) for n in nodes]

        page_nav = tal.getTAL(theme.getTemplate("content_nav.html"), ctx, macro="page_nav_prev_next", language=language)
        return page_nav, files

    @ensure_unicode_returned(name="web.frontend.content.ContentList:html")
    def html(self, req):
        language = lang(req)
        if not language:
            language = None
        if self.content:
            headline = tal.getTAL(theme.getTemplate("content_nav.html"), {"nav": self}, macro="navheadline", language=language)
            return headline + self.content.html(req)

        nodes_per_page = self.nodes_per_page or 9

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

        liststyle = getContentStyles("smallview", ls)

        if "page" in req.args or "pagenav" in req.args:
            # old page navigation
            page_nav, files = self._page_nav_numbers(nodes_per_page, language, req)
        else:
            # new prev next navigation
            page_nav, files = self._page_nav_prev_next(nodes_per_page, language, req)

        ctx = {
            "page_nav": page_nav,
            "files": files,
            "sortfields": self.sortfields, "sortfieldslist": self.getSortFieldsList(),
            "ids": ",".join(str(f.node.id) for f in files),
            "op": "", "query": req.args.get("query", "")}

        filesHTML = tal.getTAL(theme.getTemplate("content_nav.html"), ctx, macro="list_header", request=req)

        # use template of style and build html content
        ctx = {"files": files, "op": "", "language": lang(req)}

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
        if ("id" in req.args or "item" in req.args) and "searchmode" not in req.args and not (
                hasattr(self.content, "in_list") and self.content.in_list(req.args.get("id"))):
            self.content = mkContentNode(req)
        elif req.args.get("searchmode") == "simple" and req.args.get("submittype") != "change":
            self.content = simple_search(req)  # simple search
        elif req.args.get("searchmode") in ["extended", "extendedsuper"] and req.args.get("submittype") != "change":
            self.content = extended_search(req)  # extended search
        else:
            newcontent = self.content.feedback(req)
            if newcontent:
                self.content = newcontent
        if hasattr(self.content, "collection"):
            self.collection = self.content.collection
            if self.collection:
                self.collection = db.refresh(self.collection)
                self.collectionlogo = CollectionLogo(self.collection)
        if hasattr(self.content, "getParams"):
            self.params = '&' + self.content.getParams()

    def actNode(self):
        if hasattr(self.content, 'nodes'):
            if self.content.nr >= 0 and len(self.content.nodes) >= self.content.nr:
                return self.content.nodes[self.content.nr]
            else:
                return self.content.node

        elif hasattr(self.content, 'node'):
            return self.content.node
        else:
            return None

    @ensure_unicode_returned
    def html(self, req):
        if "raw" in req.args:
            path = ""
        else:
            if hasattr(self.content, "node"):
                node = self.content.node = db.refresh(self.content.node)
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
                               "searchmode": req.args.get("searchmode", ""),
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
