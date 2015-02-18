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
from mediatumtal import tal
import core.tree as tree
import os

from utils.utils import getCollection, Link, getFormatedString
from core.acl import AccessData
from core.translation import lang, t
from web.frontend import Content
from web.frontend.searchresult import simple_search, extended_search
from core.styles import getContentStyles, theme
from utils.strings import ensure_unicode_returned


logg = logging.getLogger(__name__)


class SingleFile:

    def __init__(self, file, nr, num, words=None, language=None):
        self.attachment = None
        for f in file.getFiles():
            if f.getType() == "attachment":
                self.attachment = f
                break

        if not self.attachment:
            for f in file.getFiles():
                if hasattr(file, "getSysFiles") and f.getType() not in file.getSysFiles():
                    self.attachment = f
                    break

        self.datatype = file.getType()
        self.image = file.show_node_image()
        self.text = file.show_node_text(words, language=language)
        self.fields = self.datatype.getMetaFields()
        self.thumbnail = self.image
        self.node = file
        self.nr = nr
        self.num = num
        self.file = file

    def getShoppingBagLink(self):
        return u'shoppingBag(\'{}\')'.format(self.node.id)

    def getMetadata(self, separator=".", language=None):
        return self.node.show_node_text(separator=separator, language=language)

    def getLink(self):
        return '/node?id=' + self.file.id

SORT_FIELDS = 2


class ContentList(Content):

    def __init__(self, files, collection=None, words=None):
        self.nr = -1
        self.page = 0
        self.lang = "en"
        self.words = words
        self.files = files
        self.num = len(files)
        self.collection = collection
        self.content = None
        self.id2pos = {}
        self.sortfields = [self.collection.get("sortfield")] * SORT_FIELDS
        if self.sortfields[0]:
            self.files.sort_by_fields(self.sortfields)
        ls = self.collection.get("style")
        if ls:
            ls = ls.split(";")[0]
        else:
            ls = "list"
        self.liststyle = getContentStyles("smallview", ls)

    def length(self):
        return self.num

    def actual(self):
        return "(%d/%d)" % (int(self.nr) + 1, self.num)

    def in_list(self, id):
        return id in self.id2pos

    def link_first(self):
        self.id2pos[self.files[0].id] = 0
        return "/node?id=" + self.files[0].id

    def link_last(self):
        self.id2pos[self.files[self.num - 1].id] = self.num - 1
        return "/node?id=" + self.files[self.num - 1].id

    def link_prev(self):
        if self.nr > 0:
            self.id2pos[self.files[self.nr - 1].id] = self.nr - 1
            return "/node?id=" + self.files[self.nr - 1].id
        else:
            return self.link_first()

    def link_next(self):
        if self.nr < self.num - 1:
            self.id2pos[self.files[self.nr + 1].id] = self.nr + 1
            return "/node?id=" + self.files[self.nr + 1].id
        else:
            return self.link_last()

    def link_back(self):
        return "node?back=y"

    def feedback(self, req):
        myid = req.params.get("id")
        if myid:
            try:
                self.nr = self.id2pos[myid]
            except KeyError:
                pass  # happens for first node (the directory)

        self.lang = lang(req)

        if "page" in req.params:
            self.page = int(req.params.get("page"))
            self.nr = -1

        if "back" in req.params:
            self.nr = -1

        for i in range(SORT_FIELDS):
            if ("sortfield%d" % i) in req.params:
                self.sortfields[i] = req.params["sortfield%d" % i]

        self.files.sort_by_fields(self.sortfields)

        self.content = None
        if self.nr >= 0 and self.nr < self.num:
            self.content = ContentNode(self.files[self.nr], self.nr, self.num, self.words, self.collection)

        # style selection
        if "style" in req.params:
            newstyle = req.params.get("style")
            if self.content.__class__ != ContentNode:
                req.session["liststyle-" + self.collection.id] = getContentStyles("smallview", newstyle)
            else:
                req.session[
                    "style-" +
                    self.content.node.getContentType()] = getContentStyles(
                    "bigview",
                    name=newstyle,
                    contenttype=self.content.node.getContentType())[0]
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
            if len(self.files):
                if not self.sortfields[i]:
                    sortfields += [SortChoice("", "", 0, "")]
                else:
                    sortfields += [SortChoice("", "", 0, "not selected")]
                for field in self.files[0].getMetaFields():
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

    @ensure_unicode_returned(name="web.frontend.content.ContentList:html")
    def html(self, req):
        language = lang(req)
        if not language:
            language = None
        if self.content:
            headline = tal.getTAL(theme.getTemplate("content_nav.html"), {"nav": self}, macro="navheadline", language=lang(req))
            return headline + self.content.html(req)

        nav_list = list()
        nav_page = list()

        if "itemsperpage" not in req.params:
            files_per_page = 9
        else:
            if req.params.get("itemsperpage") == "-1":
                files_per_page = len(self.files)
            else:
                files_per_page = int(req.params.get("itemsperpage"))

        min = 0
        max = (len(self.files) + files_per_page - 1) / files_per_page - 1
        left = self.page - 6
        right = self.page + 6

        if left < 0:
            left = 0
        if right > max or right >= max - 2:
            right = max
        if left <= min + 2:
            left = min

        if left > min:
            nav_list.append("/node?page=" + ustr(min))
            nav_list.append('...')
            nav_page.append(min)
            nav_page.append(-1)

        for a in range(left, right + 1):
            nav_list.append("/node?page=" + ustr(a))
            nav_page.append(a)

        if right < max:
            nav_list.append('...')
            nav_list.append("/node?page=" + ustr(max))
            nav_page.append(-1)
            nav_page.append(max)

        tal_files = []
        tal_ids = []

        i = 0
        for i in range(self.page * files_per_page, (self.page + 1) * files_per_page):
            if i < self.num:
                file = self.files[i]
                self.id2pos[self.files[i].id] = i
                tal_files += [SingleFile(file, i, self.num, language=language)]
                tal_ids += [SingleFile(file, i, self.num, language=language).node.id]
            i = i + 1

        liststyle = req.session.get("liststyle-" + self.collection.id, "")  # .split(";")[0]# user/session setting for liststyle?
        if not liststyle:
            # no liststsyle, use collection default
            liststyle = self.liststyle

        filesHTML = tal.getTAL(theme.getTemplate("content_nav.html"), {
            "nav_list": nav_list, "nav_page": nav_page, "act_page": self.page,
            "sortfields": self.sortfields, "sortfieldslist": self.getSortFieldsList(),
            "files": tal_files, "ids": ",".join(tal_ids), "maxresult": len(self.files),
            "op": "", "query": req.params.get("query", "")}, macro="files", request=req)

        # use template of style and build html content
        contentList = liststyle.renderTemplate(req, {"nav_list": nav_list, "nav_page": nav_page, "act_page": self.page,
                                                     "files": tal_files, "maxresult": len(self.files), "op": "", "language": lang(req)})

        return filesHTML + '<div id="nodes">' + contentList + '</div>' + filesHTML


# paths
def getPaths(node, access):
    list = []

    def r(node, path):
        if node is tree.getRoot():
            return
        for p in node.getParents():
            path.append(p)
            if p is not tree.getRoot("collections"):
                r(p, path)
        return path

    paths = []

    p = r(node, [])
    omit = 0
    if p:
        for node in p:
            if access.hasReadAccess(node):
                if node.type in ("directory", "home", "collection") or node.type.startswith("directory"):
                    paths.append(node)
                if node is tree.getRoot("collections") or node.type == "root":
                    paths.reverse()
                    if len(paths) > 0 and not omit:
                        list.append(paths)
                    omit = 0
                    paths = []
            else:
                omit = 1
    if len(list) > 0:
        return list
    else:
        return []


class ContentNode(Content):

    def __init__(self, node, nr=0, num=0, words=None, collection=None):
        self.node = node
        self.id = node.id
        self.paths = []
        self.nr = nr
        self.num = num
        self.words = words
        if collection:
            self.collection = collection
        else:
            self.collection = getCollection(node)
        collections = {}

    def actual(self):
        return "(%d/%d)" % (int(self.nr) + 1, self.num)

    def getContentStyles(self):
        return getContentStyles("bigview", contenttype=self.node.getContentType())

    @ensure_unicode_returned(name="web.frontend.content:html")
    def html(self, req):
        paths = u""
        stylebig = self.getContentStyles()
        liststyle = req.session.get("style-" + self.node.getContentType(), "")
        show_node_big = ensure_unicode_returned(self.node.show_node_big, name="show_node_big of %s" % self.node)

        if not self.node.isContainer():
            plist = getPaths(self.node, AccessData(req))
            paths = tal.getTAL(theme.getTemplate("content_nav.html"), {"paths": plist}, macro="paths", language=lang(req))
        # render style of node for nodebig
        if len(stylebig) > 1:
            # more than on style found
            for item in stylebig:
                if liststyle:
                    if item.getName() == liststyle.getName():
                        return getFormatedString(show_node_big(req, template=item.getTemplate())) + paths
                else:
                    if item.isDefaultStyle():
                        return getFormatedString(show_node_big(req, template=item.getTemplate())) + paths
        elif len(stylebig) == 1:
            return getFormatedString(show_node_big(req, template=stylebig[0].getTemplate())) + paths
        return getFormatedString(show_node_big(req)) + paths


def fileIsNotEmpty(file):
    with open(file) as f:
        s = f.read().strip()
    if s:
        return 1
    else:
        return 0


def mkContentNode(req):
    access = AccessData(req)
    id = req.params.get("id", tree.getRoot("collections").id)
    try:
        node = tree.getNode(id)
    except tree.NoSuchNodeError:
        return ContentError("No such node", 404)
    if not access.hasReadAccess(node):
        return ContentError("Permission denied", 403)

    if node.type in ["directory", "collection"]:
        if "files" not in req.params:
            for f in node.getFiles():
                if f.type == "content" and f.mimetype == "text/html" and os.path.isfile(
                        f.retrieveFile()) and fileIsNotEmpty(f.retrieveFile()):
                    return ContentNode(node)

        ids = access.filter(list(set(tree.getAllContainerChildrenAbs(node, []))))
        node.ccount = len(ids)
        #ids = access.filter(node.getAllChildren())
        c = ContentList(tree.NodeList(ids), getCollection(node))
        c.feedback(req)
        c.node = node
        return c
    else:
        return ContentNode(node)


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
        self.content = ContentNode(tree.getRoot("collections"))
        self.collection = None
        self.collectionlogo = None
        self.params = ""

    def getPath(self):
        path = []
        if hasattr(self.content, "node"):
            cd = self.content.node
            if cd is not None:
                path.append(Link('', cd.getLabel(), ''))
                while True:
                    parents = cd.getParents()
                    if(len(parents) == 0):
                        break
                    cd = parents[0]
                    if cd is tree.getRoot("collections") or cd is tree.getRoot():
                        break
                    path.append(Link('/?id=' + cd.id + '&dir=' + cd.id, cd.getLabel(), cd.getLabel()))
        elif hasattr(self.content, "linkname") and hasattr(self.content, "linktarget"):
            path.append(Link(self.content.linktarget, self.content.linkname, self.content.linkname))
        path.reverse()
        return path

    def feedback(self, req):
        if ("id" in req.params or "item" in req.params) and "searchmode" not in req.params and not (
                hasattr(self.content, "in_list") and self.content.in_list(req.params.get("id"))):
            self.content = mkContentNode(req)
        elif req.params.get("searchmode") == "simple" and req.params.get("submittype") != "change":
            self.content = simple_search(req)  # simple search
        elif req.params.get("searchmode") in ["extended", "extendedsuper"] and req.params.get("submittype") != "change":
            self.content = extended_search(req)  # extended search
        else:
            newcontent = self.content.feedback(req)
            if newcontent:
                self.content = newcontent
        if hasattr(self.content, "collection"):
            self.collection = self.content.collection
            if self.collection:
                self.collectionlogo = CollectionLogo(self.collection)
        if hasattr(self.content, "getParams"):
            self.params = '&' + self.content.getParams()

    def actNode(self):
        if hasattr(self.content, 'files'):
            if self.content.nr >= 0 and len(self.content.files) >= self.content.nr:
                return self.content.files[self.content.nr]
            else:
                return self.content.node

        elif hasattr(self.content, 'node'):
            return self.content.node
        else:
            return None

    @ensure_unicode_returned
    def html(self, req):
        styles = []
        nodeprint = "1"  # show print icon
        styles = self.content.getContentStyles()

        if "raw" in req.params:
            path = ""
        else:
            items = req.params.get("itemsperpage")
            try:
                id = self.content.node.id
                node = self.content.node

                if not node.getContentType() in ['collection', 'directory']:
                    nodeprint = 0
                else:
                    if node.get("system.print") != "":
                        nodeprint = node.get("system.print")
            except:
                logg.exception("exception in ContentArea.html, setting id = 0")
                id = 0

            printlink = '/print/' + ustr(id)
            if nodeprint == "1" and "sortfield0" in req.params.keys():
                printlink += '?sortfield0=' + ustr(req.params.get("sortfield0")) + '&sortfield1=' + ustr(req.params.get("sortfield1"))

            if req.params.get("show_navbar") == 0 or req.session.get("area") == "publish":
                breadscrubs = []
            else:
                try:
                    breadscrubs = self.getPath()
                except AttributeError:
                    logg.exception("exception in html")
                    return req.error(404, "Object cannot be shown")

            path = tal.getTAL(theme.getTemplate("content_nav.html"),
                              {"params": self.params,
                               "path": breadscrubs,
                               "styles": styles,
                               "logo": self.collectionlogo,
                               "searchmode": req.params.get("searchmode", ""),
                               "items": items,
                               "id": id,
                               "nodeprint": nodeprint,
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

        if self.path != "":
            self.path = '/file/' + ustr(self.collection.id) + '/' + self.path

    def getPath(self):
        return self.path

    def getURL(self):
        return self.collection.get("url")

    def getShowOnHTML(self):
        return self.collection.get("showonhtml")


def getContentArea(req):
    if len(req.params):
        if "contentarea" in req.session:
            c = req.session["contentarea"]
        else:
            c = req.session["contentarea"] = ContentArea()
        return c
    else:
        c = req.session["contentarea"] = ContentArea()
        return c
