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

from core import Node, db, webconfig
from core.systemtypes import Root
from core.translation import t, lang
from core.transition import current_user
from contenttypes import Container
from utils.fileutils import importFile
from utils.utils import EncryptionException, dec_entry_log
from utils.pathutils import get_accessible_paths
from utils.compat import iteritems
from web.frontend.content import get_make_search_content_function
from web.frontend.search import NoSearchResult
import re
import urllib


logg = logging.getLogger(__name__)
q = db.query

default_edit_nodes_per_page = 20
edit_node_per_page_values = [20, 50, 100, 200]

class NodeWrapper:

    def __init__(self, node, nodenumber):
        self.node = node
        self.nodenumber = nodenumber

    def getNode(self):
        return self.node

    def getNodeNumber(self):
        return self.nodenumber


class EditorNavList:

    def __init__(self):
        self.nav_params = None
        self.nav_searchparams = {}
        self.nodes_per_page = default_edit_nodes_per_page
        self.page = 1

    def nav_link(self, **param_overrides):
        params = {}
        # params = self.nav_params.copy()
        params = self.nav_searchparams.copy()
        params["page"] = self.page

        if not "page" in param_overrides:
            if self.page:
                params["page"] = self.page

        params.update(param_overrides)
        params = {k: v.encode('utf-8') if not isinstance(v, int) else v for k, v in iteritems(params) if v is not None and v != ""}
        return '/edit/edit_content?' + urllib.urlencode(params)


class EditorNodeList:

    def __init__(self, nodes):
        self.nodeids = []
        self.nodeid2pos = {}
        i = 0
        for node in nodes:
            try:
                if not node.isContainer():
                    self.nodeids.append(node.id)
                    self.nodeid2pos[node.id] = i
                    i += 1
            except TypeError:
                continue

    def getNext(self, nodeid):
        try:
            pos = self.nodeid2pos[int(nodeid)]
        except KeyError:
            return None
        if pos >= len(self.nodeids) - 1:
            return None
        return self.nodeids[pos + 1]

    def getPrevious(self, nodeid):
        try:
            pos = self.nodeid2pos[int(nodeid)]
        except KeyError:
            return None
        if pos <= 0:
            return None
        return self.nodeids[pos - 1]

    def getPositionString(self, nodeid):
        try:
            pos = self.nodeid2pos[int(nodeid)]
        except KeyError:
            return "", ""
        return pos + 1, len(self.nodeids)

    def getPositionCombo(self, tab):
        script = """<script language="javascript">
        function gotoContent(cid, tab) {
          window.location.assign('/edit/edit_content?id='+cid+'&tab='+tab);
        }
        </script>"""
        data = []
        for nid in self.nodeids:
            data.append((nid, len(data) + 1))
        return data, script


def edit_sort_by_fields(query, field, idx=-1):
    if idx >= 0:
        nodes = query
    if isinstance(field, basestring):
        # handle some special cases
        if not field or field == "id" or field == "off":
            if idx >= 0:
                return ''
            return query.order_by(Node.id)
        elif field == "name" or field == "nodename":
            if idx >= 0:
                return nodes[idx].name
            return query.order_by(Node.name)
        elif field == "-name" or field == "-nodename":
            if idx >= 0:
                return nodes[idx].name
            return query.order_by(Node.name.desc())
        elif field == "orderpos":
            if idx >= 0:
                print idx
                return nodes[idx].orderpos
            return query.order_by(Node.orderpos)
        elif field == "-orderpos":
            if idx >= 0:
                return nodes[idx].orderpos
            return query.order_by(Node.orderpos.desc())
        else:
            fields = [field]
    else:
        # remove empty sortfields
        fields = [f for f in field if f]
        if not fields:
            # no fields left, all empty...
            if idx >= 0:
                return nodes[idx]
            return query

    for field in fields:
        if field.startswith("-"):
            if idx >= 0:
                return nodes[idx].get(field[1:])
            query = query.order_by(Node.attrs[field[1:]].desc())
        else:
            if idx >= 0:
                return nodes[idx].get(field)
            query = query.order_by(Node.attrs[field])

    if idx >= 0:
        return nodes[idx]
    return query


def searchbox_navlist_height(req, item_count):
    searchmode = req.params.get("searchmode")
    bottom = 93 + 15 if item_count[0] < item_count[1] else 93
    return bottom if not searchmode else bottom + 67 if searchmode == "extended" else bottom + 256

# simple nodelist cache which is filled in showdir() and used by shownav() and get_ids_from_req() to avoid
# a recomputing of nodelist, especially if search is used
# each entry has the request_number as key and the nodelist as value
# after the page is rendered the entry is no longer needed and is deleted with delete_g_nodes_entry()
g_nodes = {}

@dec_entry_log
def delete_g_nodes_entry(req):
    if req.request_number in g_nodes.keys():
        del g_nodes[req.request_number]

@dec_entry_log
def shownav(req, node, publishwarn="auto", markunpublished=False, sortfield=None):
    page = int(req.params.get('page', 1))
    # showdir must be called before shownav, so g_nodes can be used from showdir
    return shownavlist(req, node, g_nodes[req.request_number], page, dir=node)


@dec_entry_log
def showdir(req, node, publishwarn="auto", markunpublished=False, sortfield=None, item_count=None, all_nodes=None):
    global g_nodes
    if publishwarn == "auto":
        homedirs = current_user.home_dir.all_children_by_query(q(Container))
        publishwarn = node in homedirs
    nodes = node.content_children # XXX: ?? correct
    make_search_content = get_make_search_content_function(req)
    paths = get_accessible_paths(node, q(Node).prefetch_attrs())
    if make_search_content:
        content_or_error = make_search_content(req, paths)
        if content_or_error:
            if isinstance(content_or_error, NoSearchResult):
                nodes = []
            else:
                nodes = content_or_error.node_query

    if sortfield is None:
        sortfield = req.params.get('sortfield')
    if not sortfield:
        sortfield = node.get("sortfield")
    if nodes:
        if sortfield and sortfield != "off":
            nodes = edit_sort_by_fields(nodes, sortfield).all()
        else:
            nodes = edit_sort_by_fields(nodes, "id").all()
    # set g_nodes to be used by shownav which must be called after showdir
    g_nodes[req.request_number] = nodes
    page = int(req.params.get('page', 1))
    return shownodelist(req, nodes, page, publishwarn=publishwarn, markunpublished=markunpublished, dir=node,
                        item_count=item_count, all_nodes=all_nodes)


def getAllSubDirs(node):
    dirs = []
    for c in node.getChildren():
        if c.type == "directory":
            dirs += [c] + getAllSubDirs(c)
    return dirs


@dec_entry_log
def showoperations(req, node):
    return ""

def get_nodes_per_page(req, dir):
    nodes_per_page = req.params.get('nodes_per_page', '')
    if nodes_per_page:
        nodes_per_page = int(nodes_per_page)
    else:
        if dir:
            nodes_per_page = dir.get('nodes_per_page')
            if nodes_per_page:
                nodes_per_page = int(nodes_per_page)
    if not nodes_per_page:
        nodes_per_page = default_edit_nodes_per_page
    return nodes_per_page

re_searchparams = re.compile("(query\d*|field\d+|searchmode)")

def get_searchparams(req):
    searchparams = {k: v for k, v in req.args.items() if re.match(re_searchparams, k)}
    return searchparams


@dec_entry_log
def shownavlist(req, node, nodes, page, dir=None):
    nodes_per_page = get_nodes_per_page(req, dir)

    c = EditorNavList()
    c.nodes_per_page = nodes_per_page
    c.nodes_per_page_from_req = nodes_per_page
    c.nav_params = {k: v for k, v in req.args.items()
                    if k not in ("style", "sortfield", "page", "nodes_per_page")}
    c.nav_searchparams = get_searchparams(req)
    if isinstance(nodes, list):
        nodes_len = len(nodes)
    else:
        nodes_len = nodes.count()
    if req.params.get("action", "") == "resort":
        sortfield = req.params.get("value", "")
    else:
        sortfield = req.params.get("sortfield", "")
    if not sortfield:
        sortfield = node.get("sortfield")
    node_id = req.params.get("id", "")
    end_idx = nodes_len/nodes_per_page + (1 if nodes_len % nodes_per_page == 0 else 2)
    nav_page = [x for x in range(1, end_idx)]
    nav_list = [c.nav_link(id=node_id, page=p, nodes_per_page=nodes_per_page, sortfield=sortfield) for p in nav_page]
    nav_tooltip = []
    node_idx = 0
    if nodes_len:
        for p in nav_page:
            tooltip = edit_sort_by_fields(nodes, sortfield, node_idx)
            if isinstance(tooltip, basestring):
                if len(tooltip) > 13:
                    tooltip = tooltip[:10] + '...'
            else:
                tooltip = str(tooltip)
            nav_tooltip.append(tooltip)
            node_idx += nodes_per_page
    ctx = {
        "act_page": page,
        "nav_list" : nav_list,
        "nav_tooltip" : nav_tooltip,
        "nav_page" : nav_page,
    }
    page_nav = req.getTAL("web/edit/edit_nav.html", ctx, macro="page_nav_prev_next")
    return page_nav


@dec_entry_log
def shownodelist(req, nodes, page, publishwarn=True, markunpublished=False, dir=None, item_count=None, all_nodes=None):
    req.session["nodelist"] = EditorNodeList(nodes)
    script_array = "allobjects = new Array();\n"
    nodelist = []
    nodes_per_page = get_nodes_per_page(req, dir)

    start = (page - 1) * nodes_per_page
    end = start + nodes_per_page

    user = current_user
    nodes_in_page = nodes[start:end]
    all_nodes = nodes[:]
    if isinstance(item_count, list):
        item_count.append(len(nodes_in_page))
        item_count.append(len(all_nodes))

    for child in nodes_in_page:
        from contenttypes import Content
        if isinstance(child, Content):
            script_array += "allobjects['%s'] = 0;\n" % child.id
            nodelist.append(child)

    chkjavascript = ""
    notpublished = {}
    if publishwarn or markunpublished:
        homedirs = user.home_dir.all_children_by_query(q(Container))
        if markunpublished:
            chkjavascript = """<script language="javascript">"""
        for node in nodes_in_page:
            ok = 0
            for p in node.parents:
                if p not in homedirs:
                    ok = 1
            if not ok:
                if markunpublished:
                    chkjavascript += """allobjects['check%s'] = 1;
                                        document.getElementById('check%s').checked = true;
                                     """ % (node.id, node.id)

                notpublished[node] = node
        chkjavascript += """</script>"""
        # if all nodes are properly published, don't bother
        # to warn the user
        if not notpublished:
            publishwarn = 0

    unpublishedlink = None
    if publishwarn:
        if dir:
            uploaddir = dir
        else:
            uploaddir = user.upload_dir
        unpublishedlink = "edit_content?tab=publish&id=" + unicode(uploaddir.id)

    html = req.getTAL("web/edit/edit_common.html", {"notpublished": notpublished,
                                                    "chkjavascript": chkjavascript,
                                                    "unpublishedlink": unpublishedlink,
                                                    "nodelist": nodelist,
                                                    "script_array": script_array,
                                                    "language": lang(req)},
                      macro="show_nodelist")
    return html


def isUnFolded(unfoldedids, id):
    try:
        return unfoldedids[id]
    except:
        unfoldedids[id] = 0
        return 0


@dec_entry_log
def writenode(req, node, unfoldedids, f, indent, key, ret=""):
    if node.type not in ["directory", "collection", "root", "home", "collections", "navigation"] and not node.type.startswith("directory"):
        return ret
    if not node.has_read_access():
        return ret

    isunfolded = isUnFolded(unfoldedids, node.id)

    num = 0
    objnum = 0
    children = node.getChildren().sort_by_orderpos()

    num = len(node.getContainerChildren())
    objnum = len(node.getContentChildren())

    # for c in children:
    #     if c.type in["directory", "collection"] or c.type.startswith("directory"):
    #         num += 1
    #     else:
    #         objnum += 1

    if num:
        if isunfolded:
            ret += f(req, node, objnum, "edit_tree?tree_fold=" +
                     node.id, indent, type=1)
        else:
            ret += f(req, node, objnum, "edit_tree?tree_unfold=" +
                     node.id, indent, type=2)
    else:
        ret += f(req, node, objnum, "", indent, type=3)

    if isunfolded:
        for c in children:
            ret += writenode(req, c, unfoldedids, f, indent + 1, key)
    return ret


@dec_entry_log
def writetree(req, node, f, key="", openednodes=None, sessionkey="unfoldedids", omitroot=0):
    ret = ""

    try:
        unfoldedids = req.session[sessionkey]
        len(unfoldedids)
    except:
        req.session[sessionkey] = unfoldedids = {unicode(q(Root).one().id): 1}

    if openednodes:
        # open all selected nodes and their parent nodes
        def o(u, n):
            u[n.id] = 1
            for n in n.parents:
                o(u, n)
        for n in openednodes:
            o(unfoldedids, n)
        req.session[sessionkey] = unfoldedids

    try:
        unfold = req.params["tree_unfold"]
        unfoldedids[unfold] = 1
    except KeyError:
        pass

    try:
        fold = req.params["tree_fold"]
        unfoldedids[fold] = 0
    except KeyError:
        pass

    if omitroot:
        for c in node.getChildren().sort("name"):
            ret += writenode(req, c, unfoldedids, f, 0, key)
    else:
        ret += writenode(req, node, unfoldedids, f, 0, key)

    return ret


def upload_help(req):
    try:
        return req.writeTAL("contenttypes/" + req.params.get("objtype", "") + ".html", {}, macro="upload_help")
    except:
        None


@dec_entry_log
def send_nodefile_tal(req):
    if "file" in req.params:
        return upload_for_html(req)

    id = req.params.get("id")
    node = q(Node).get(id)

    if not (node.has_read_access() and node.has_write_access() and node.has_data_access() and isinstance(node, Container)):
        return ""

    def fit(imagefile, cn):
        # fits the image into a box with dimensions cn, returning new width and
        # height
        try:
            import PIL
            sz = PIL.Image.open(imagefile).size
            (x, y) = (sz[0], sz[1])
            if x > cn[0]:
                y = (y * cn[0]) / x
                x = (x * cn[0]) / x
            if y > cn[1]:
                x = (x * cn[1]) / y
                y = (y * cn[1]) / y
            return (x, y)
        except:
            return cn

    # only pass images to the file browser
    files = [f for f in node.files if f.mimetype.startswith("image")]

    # this flag may switch the display of a "delete" button in the customs
    # file browser in web/edit/modules/startpages.html
    showdelbutton = True
    return req.getTAL("web/edit/modules/startpages.html", {"id": id, "node": node, "files": files, "fit": fit, "logoname": node.get("system.logo"), "delbutton": True}, macro="fckeditor_customs_filemanager")


@dec_entry_log
def upload_for_html(req):
    user = current_user
    datatype = req.params.get("datatype", "image")

    id = req.params.get("id")
    node = q(Node).get(id)

    if not (node.has_read_access() and node.has_write_access() and node.has_data_access()):
        return 403

    for key in req.params.keys():
        if key.startswith("delete_"):
            filename = key[7:-2]
            # XXX: dead code?
            for file in node.files:
                if file.base_name == filename:
                    node.files.remove(file)
            db.session.commit()

    if "file" in req.params.keys():  # file

        # file upload via (possibly disabled) upload form in custom image
        # browser
        file = req.params["file"]
        del req.params["file"]
        if hasattr(file, "filesize") and file.filesize > 0:
            try:
                logg.info("file %s (temp %s) uploaded by user %s (%s)", file.filename, file.tempname, user.login_name, user.id)
                nodefile = importFile(file.filename, file.tempname)
                node.files.append(nodefile)
                db.session.commit()
                req.request["Location"] = req.makeLink(
                    "nodefile_browser/%s/" % id, {})
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {
                                                       "id": id, "tab": "tab_editor", "error": "EncryptionError_" + datatype[:datatype.find("/")]})
            except:
                logg.exception("error during upload")
                req.request["Location"] = req.makeLink("content", {
                                                       "id": id, "tab": "tab_editor", "error": "PostprocessingError_" + datatype[:datatype.find("/")]})
            return send_nodefile_tal(req)

    if "upload" in req.params.keys():  # NewFile
        # file upload via CKeditor Image Properties / Upload tab
        file = req.params["upload"]
        del req.params["upload"]
        if hasattr(file, "filesize") and file.filesize > 0:
            try:
                logg.info("%s upload via ckeditor %s (%s)", user.login_name , file.filename, file.tempname)
                nodefile = importFile(file.filename, file.tempname)
                node.files.append(nodefile)
                db.session.commit()
            except EncryptionException:
                req.request["Location"] = req.makeLink("content", {
                                                       "id": id, "tab": "tab_editor", "error": "EncryptionError_" + datatype[:datatype.find("/")]})
            except:
                logg.exception("error during upload")
                req.request["Location"] = req.makeLink("content", {
                                                       "id": id, "tab": "tab_editor", "error": "PostprocessingError_" + datatype[:datatype.find("/")]})

            url = '/file/' + id + '/' + file.tempname.split('/')[-1]

            res = """<script type="text/javascript">

                // Helper function to get parameters from the query string.
                function getUrlParam(paramName)
                {
                  var reParam = new RegExp('(?:[\?&]|&amp;)' + paramName + '=([^&]+)', 'i') ;
                  var match = window.location.search.match(reParam) ;

                  return (match && match.length > 1) ? match[1] : '' ;
                }
            funcNum = getUrlParam('CKEditorFuncNum');

            window.parent.CKEDITOR.tools.callFunction(funcNum, "%(fileUrl)s","%(customMsg)s");

            </script>;""" % {
                'fileUrl': url.replace('"', '\\"'),
                'customMsg': (t(lang(req), "edit_fckeditor_cfm_uploadsuccess")),
            }

            return res

    return send_nodefile_tal(req)


def get_special_dir_type(node):
    return node.system_attrs.get("used_as", None)


def get_edit_label(node, lang):
    special_dir_type = get_special_dir_type(node)

    if special_dir_type is None:
        label = node.getLabel(lang=lang)
    elif special_dir_type == "home":
        label = t(lang, 'user_home')
        if current_user.is_admin:
            label += " (" + node.name + ")"
    else:
        label = t(lang, 'user_' + special_dir_type)

    return label
