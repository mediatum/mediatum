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

from core import Node, db
from core.systemtypes import Root
from core.translation import t, lang
from core.transition import current_user
from contenttypes import Container
from utils.fileutils import importFile
from utils.utils import EncryptionException, dec_entry_log


logg = logging.getLogger(__name__)
q = db.query

class NodeWrapper:

    def __init__(self, node, nodenumber):
        self.node = node
        self.nodenumber = nodenumber

    def getNode(self):
        return self.node

    def getNodeNumber(self):
        return self.nodenumber


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


@dec_entry_log
def showdir(req, node, publishwarn="auto", markunpublished=False, sortfield=None):
    if publishwarn == "auto":
        homedirs = current_user.home_dir.all_children_by_query(q(Container))
        publishwarn = node in homedirs
    nodes = node.content_children # XXX: ?? correct
    if sortfield is None:
        sortfield = node.get("sortfield")
    if sortfield:
        nodes = nodes.sort_by_fields([sortfield])
    return shownodelist(req, nodes, publishwarn=publishwarn, markunpublished=markunpublished, dir=node)


def getAllSubDirs(node):
    dirs = []
    for c in node.getChildren():
        if c.type == "directory":
            dirs += [c] + getAllSubDirs(c)
    return dirs


@dec_entry_log
def showoperations(req, node):
    return ""


@dec_entry_log
def shownodelist(req, nodes, publishwarn=True, markunpublished=False, dir=None):
    req.session["nodelist"] = EditorNodeList(nodes)
    script_array = "allobjects = new Array();\n"
    nodelist = []

    user = current_user

    for child in nodes:
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
        for node in nodes:
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

    return req.getTAL("web/edit/edit_common.html", {"notpublished": notpublished,
                                                    "chkjavascript": chkjavascript,
                                                    "unpublishedlink": unpublishedlink,
                                                    "nodelist": nodelist,
                                                    "script_array": script_array,
                                                    "language": lang(req)},
                      macro="show_nodelist")


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