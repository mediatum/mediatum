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
import sys
import os
import time
import json
import core.config as config
import core.help as help
import core.translation
from core import Node

from contenttypes import Container, Collections, Data, Home
from core.systemtypes import Root
from utils.utils import Menu, splitpath, parseMenuString
from edit_common import *

from core.translation import lang
from core.translation import t as translation_t
from core.transition import httpstatus

from edit_common import EditorNodeList
from utils.utils import funcname, get_user_id, dec_entry_log


from core import db

logg = logging.getLogger(__name__)
q = db.query


def getTreeLabel(node, lang=None):
    try:
        label = node.getLabel(lang=lang)
    except:
        try:
            label = node.getLabel()
        except:
            label = node.getName()

    c = len(node.getContentChildren())
    if c > 0:
        label += ' <small>(%s)</small>' % (c)
    return label


def getEditorIconPath(node, req=None):
    '''
    retrieve icon path for editor tree relative to img/
    '''
    if req:
        name = node.name
        label = node.getLabel(req)

        if name == 'home' or name.startswith('Arbeitsverzeichnis') or name.startswith(translate('user_directory', request=req)) or label.startswith(translate('user_directory', request=req)):
            return 'webtree/homeicon.gif'
        elif name == 'Uploads' or name.startswith(translate('user_upload', request=req)) or label.startswith(translate('user_upload', request=req)):
            return 'webtree/uploadicon.gif'
        elif name == 'Importe' or name.startswith(translate('user_import', request=req)) or label.startswith(translate('user_import', request=req)):
            return 'webtree/importicon.gif'
        elif name == 'Inkonsistente Daten' or name.startswith(translate('user_faulty', request=req)) or label.startswith(translate('user_faulty', request=req)):
            return 'webtree/faultyicon.gif'
        elif node.name == 'Papierkorb' or name.startswith(translate('user_directory', request=req)) or label.startswith(translate('user_directory', request=req)):
            return 'webtree/trashicon.gif'

    if hasattr(node, 'treeiconclass'):
        return "webtree/" + node.treeiconclass() + ".gif"
    else:
        return "webtree/" + node.getContentType() + ".gif"


def get_editor_icon_path_from_nodeclass(cls):
    '''
    retrieve icon path for editor tree relative to img/
    '''

    if hasattr(cls, 'treeiconclass'):
        return u"webtree/{}.gif".format(cls.treeiconclass())
    else:
        return u"webtree/{}.gif".format(cls.__name__)


def getIDPaths(nid, access, sep="/", containers_only=True):
    '''
    return list of sep-separated id lists for paths to node with id nid
    '''
    try:
        node = tree.getNode(nid)
        if not access.hasReadAccess(node):
            return []
    except:
        return []
    from web.frontend.content import getPaths
    paths = getPaths(node, access)
    res = []
    for path in paths:
        if containers_only:
            pids = [("%s" % p.id)
                    for p in path if hasattr(p, 'isContainer') and p.isContainer()]
        else:
            pids = [("%s" % p.id) for p in path]
        if pids:
            res.append(sep.join(pids))
    return res


def frameset(req):
    id = req.params.get("id", q(Collections).one().id)
    tab = req.params.get("tab", None)
    language = lang(req)

    access = AccessData(req)
    if not access.getUser().isEditor():
        req.writeTAL("web/edit/edit.html", {}, macro="error")
        req.writeTAL("web/edit/edit.html",
                     {"id": id, "tab": (tab and "&tab=" + tab) or ""}, macro="edit_notree_permission")
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return

    currentdir = q(Data).get(id)

    if currentdir is None:
        currentdir = q(Collections).one()
        req.params["id"] = currentdir.id
        id = req.params.get("id")

    nodepath = []
    n = currentdir
    while n:
        nodepath = [n] + nodepath
        p = n.getParents()
        if p:
            n = p[0]
        else:
            n = None

    path = nidpath = ['%s' % p.id for p in nodepath]
    containerpath = [('%s' % p.id) for p in nodepath if isinstance(p, Container)]

    user = users.getUserFromRequest(req)
    menu = filterMenu(getEditMenuString(currentdir.getContentType()), user)

    spc = [Menu("sub_header_frontend", "../", target="_parent")]
    if user.isAdmin():
        spc.append(
            Menu("sub_header_administration", "../admin", target="_parent"))

    if user.isWorkflowEditor():
        spc.append(Menu("sub_header_workflow", "../publish", target="_parent"))

    spc.append(Menu("sub_header_logout", "../logout", target="_parent"))

    def getPathToFolder(node):
        n = node
        path = []
        while n:
            path = ['/%s' % (n.id)] + path
            p = n.getParents()
            if p:
                n = p[0]
            else:
                n = None
        return (node, "".join(path[2:]))

    def _getIDPath(nid, sep="/", containers_only=True):
        res = getIDPaths(nid, access, sep=sep, containers_only=containers_only)
        return res

    folders = {'homedir': getPathToFolder(users.getHomeDir(user)), 'trashdir': getPathToFolder(users.getSpecialDir(
        user, 'trash')), 'uploaddir': getPathToFolder(users.getSpecialDir(user, 'upload')), 'importdir': getPathToFolder(users.getSpecialDir(user, 'import'))}

    containertypes = [Container.__mapper__.polymorphic_map[n].class_ for n in Container.__mapper__._acceptable_polymorphic_identities if n not in ("collections", "home")]
    cmenu_iconpaths = []

    for ct in containertypes:
        ct_name = ct.__name__
        # translations of ct_name will be offered in editor tree context menu
        cmenu_iconpaths.append(
            [ct_name, translation_t(language, ct_name), get_editor_icon_path_from_nodeclass(ct)])

    # a html snippet may be inserted in the editor header
    header_insert = q(Collections).one().get('system.editor.header.insert.' + language).strip()
    help_link = q(Collections).one().get('system.editor.help.link.' + language).strip()
    homenodefilter = req.params.get('homenodefilter', '')

    v = {
        "id": id,
        "tab": (tab and "&tab=" + tab) or "",
        'user': user,
        'spc': spc,
        'folders': folders,
        'collectionsid': q(Collections).one().id,
        "basedirs": [q(Home).one(), q(Collections).one()],
        'cmenu_iconpaths': cmenu_iconpaths,
        'path': path,
        'containerpath': containerpath,
        'language': lang(req),
        't': translation_t,
        '_getIDPath': _getIDPath,
        'system_editor_header_insert': header_insert,
        'system_editor_help_link': help_link,
        'homenodefilter': homenodefilter,
       }

    req.writeTAL("web/edit/edit.html", v, macro="edit_main")


def getBreadcrumbs(menulist, tab):
    for menuitem in menulist:
        for item in menuitem.getItemList():
            if item == tab or tab.startswith(item) or item.startswith(tab):
                return [menuitem.getName(), "*" + item]
    return [tab]


def filterMenu(menuitems, user):
    hide = users.getHideMenusForUser(user)
    ret = []
    for menu in parseMenuString(menuitems):
        i = []
        for item in menu.getItemList():
            if item not in hide:
                i.append(item)
        menu.item = i
        ret.append(menu)

    return ret


def handletabs(req, ids, tabs):
    user = users.getUserFromRequest(req)
    language = lang(req)

    n = q(Data).get(ids[0])
    if n.type.startswith("workflow"):
        n = q(Root).one()

    menu = filterMenu(getEditMenuString(n.getContentType()), user)

    spc = [Menu("sub_header_frontend", "../", target="_parent")]
    if user.isAdmin():
        spc.append(
            Menu("sub_header_administration", "../admin", target="_parent"))

    if user.isWorkflowEditor():
        spc.append(Menu("sub_header_workflow", "../publish", target="_parent"))

    spc.append(Menu("sub_header_logout", "../logout", target="_parent"))

    # a html snippet may be inserted in the editor header
    help_link = q(Collections.attrs['system.editor.help.link.' + language]).scalar().strip()
    ctx = {
            "user": user,
            "ids": ids,
            "idstr": ",".join(ids),
            "menu": menu,
            "hashelp": help.getHelpPath(['edit', 'modules', req.params.get('tab') or tabs]),
            "breadcrumbs": getBreadcrumbs(menu, req.params.get("tab", tabs)),
            "spc": spc,
            "system_editor_help_link": help_link,
            }
    return req.getTAL("web/edit/edit.html", ctx, macro="edit_tabs")


def error(req):
    req.writeTAL("<tal:block tal:replace=\"errormsg\"/>",
                 {"errormsg": req.params.get("errmsg", "")}, macro="edit_errorpage")
    return httpstatus.HTTP_OK


# delivers all edit modules
editModules = {}


def getEditModules(force=0):
    if len(editModules) == 0:

        for modpath in core.editmodulepaths:  # paths with edit modules
            path = os.walk(os.path.join(config.basedir, modpath[1]))
            for root, dirs, files in path:
                for name in [f for f in files if f.endswith(".py") and f != "__init__.py"]:
                    basename = name[:-3]
                    try:
                        path, module = splitpath(modpath[1])
                        if modpath[0] == '':
                            m = __import__("web.edit.modules." + basename)
                            m = eval("m.edit.modules." + basename)
                        else:
                            sys.path += [path]
                            m = __import__(
                                module.replace("/", ".") + "." + basename)
                            m = eval("m." + name[:-3])
                        editModules[name[:-3]] = m
                    except ImportError as e:
                        print e
                        logg.exception("import error in module %s", basename)
                    except SyntaxError:
                        logg.exception("syntax error in module %s", basename)

    return editModules


def getIDs(req):
    # update nodelist, if necessary
    if "nodelist" in req.params:
        nodelist = []
        for id in req.params.get("nodelist").split(","):
            nodelist.append(tree.getNode(id))
        req.session["nodelist"] = EditorNodeList(nodelist)

    # look for one "id" parameter, containing an id or a list of ids
    id = req.params.get("id")

    try:
        id = req.params["id"]
    except KeyError:
        pass
    else:
        idlist = id.split(",")
        if idlist != ['']:
            return idlist

    # look for a pattern, a source folder and an id list
    ids = req.params.get('ids', '')

    try:
        srcid = req.params.get("src")
        if srcid == "":
            raise KeyError
        src = tree.getNode(srcid)
    except KeyError:
        src = None

    idlist = ids.split(',')
    if idlist == ['']:
        idlist = []
    return idlist


def nodeIsChildOfNode(node1, node2):
    if node1.id == node2.id:
        return 1
    for c in node2.getChildren():
        if nodeIsChildOfNode(node1, c):
            return 1
    return 0


@dec_entry_log
def edit_tree(req):
    access = AccessData(req)
    language = lang(req)
    user = users.getUserFromRequest(req)
    home_dir = users.getHomeDir(user)
    match_result = ''
    match_error = False

    if req.params.get('key') == 'root':
        nodes = q(Collections).one().container_children.sort_by_orderpos()
    elif req.params.get('key') == 'home':
        if not user.isAdmin():
            nodes = [home_dir]
        else:
            homenodefilter = req.params.get('homenodefilter', '')
            if homenodefilter:
                nodes = []
                try:
                    pattern = re.compile(homenodefilter)
                    nodes = q(Home).one().container_children.sort_by_orderpos()
                    # filter out shoppingbags etc.
                    nodes = [n for n in nodes if n.isContainer()]
                    # filter user name - after first "("
                    nodes = filter(lambda n: re.match(homenodefilter, n.getLabel(language).split('(', 1)[-1]), nodes)
                    match_result = '#=%d' % len(nodes)
                except Exception as e:
                    logg.exception("exception in pattern matching for home nodes, exception ignored")
                    match_result = '<span style="color:red">Error: %r</span>' % ustr(e)
                    match_error = True
                if home_dir not in nodes:
                    if not match_error:
                        match_result = '#=%d+1' % len(nodes)
                    nodes.append(home_dir)
                nodes = tree.NodeList(nodes).sort_by_orderpos()
            else:
                nodes = [home_dir]
    else:
        nodes = core.tree.getNode(
            req.params.get('key')).getContainerChildren().sort_by_orderpos()
        # filter out shoppingbags etc.
        nodes = [n for n in nodes if n.isContainer()]

    data = []

    # wn 2014-03-14
    # special directories may be handled in a special way by the editor
    special_dir_ids = {}
    special_dir_ids[home_dir.id] = 'userhomedir'
    for dir_type in ['upload', 'import', 'faulty', 'trash']:
        special_dir_ids[users.getSpecialDir(user, dir_type).id] = dir_type

    spec_dirs = ['userhomedir', 'upload', 'import', 'faulty', 'trash']
    spec_dir_icons = ["homeicon.gif", "uploadicon.gif",
                      "importicon.gif", "faultyicon.gif", "trashicon.gif"]

    for node in nodes:

        if not access.hasReadAccess(node):
            continue

        # try:
        #    label = node.getLabel()
        # except:
        #    label = node.getName()
        #
        # c = len(node.getContentChildren())
        #  if c>0:
        #     label += ' <small>(%s)</small>' %(c)

        label = getTreeLabel(node, lang=language)

        nodedata = {'title': label, 'key': node.id, 'lazy': True, 'folder': True,
                    'readonly': 0, 'tooltip': '%s (%s)' % (node.getLabel(lang=language),
                                                           node.id)}
        nodedata['icon'] = getEditorIconPath(node, req)

        if len(node.getContainerChildren()) == 0:
            nodedata['lazy'] = False
            nodedata['children'] = []

        if not access.hasWriteAccess(node):
            if req.params.get('key') == 'home':
                continue
            nodedata['readonly'] = 1
            nodedata['noLink'] = True

            nodedata['extraClasses'] = 'readonly'  # fancytree

        else:
            nodedata['readonly'] = 0



        nodedata['this_node_is_special'] = []
        if node.id in special_dir_ids:
            nodedata['this_node_is_special'] = nodedata[
                'this_node_is_special'] + [special_dir_ids[node.id]]
            if node.id == home_dir.id:
                nodedata['match_result'] = match_result

        data.append(nodedata)

    return req.write(json.dumps(data, indent=4))


def getEditMenuString(ntype, default=0):
    menu_str = ""

    for dtype in Data.get_all_datatypes():  # all known datatypes
        if dtype.name == ntype:
            n = tree.Node(u"", type=dtype.name)
            menu_str = getRoot().get("edit.menu." + dtype.name)
            if (menu_str == "" or default == 1) and hasattr(n, "getEditMenuTabs"):
                menu_str = n.getEditMenuTabs()
            break
    return menu_str


@dec_entry_log
def action(req):
    global editModules
    access = AccessData(req)
    language = lang(req)
    user = users.getUserFromRequest(req)

    trashdir = users.getTrashDir(user)
    uploaddir = users.getUploadDir(user)
    faultydir = users.getFaultyDir(user)
    importdir = users.getImportDir(user)

    trashdir_parents = trashdir.getParents()
    action = req.params.get("action", "")
    changednodes = {}

    if not access.user.isEditor():
        req.write("""permission denied""")
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return

    if "tab" in req.params:
        tab = req.params.get("tab").split("_")[-1]
        return editModules[tab].getContent(req, [req.params.get("id")])

    if action == "getlabels":
        nids = req.params.get('ids', [])
        nids = [nid.strip() for nid in nids.split(',') if nid.strip()]

        for nid in set(nids + [_n.id for _n in [trashdir, uploaddir, importdir, faultydir]]):
            try:
                changednodes[nid] = getTreeLabel(
                    tree.getNode(nid), lang=language)
            except:
                logg.exception("exception ignored: could not make fancytree label for node %s", nid)
        res_dict = {'changednodes': changednodes}
        req.write(json.dumps(res_dict, indent=4))
        return

    else:
        # all 'action's except 'getlabels' require a base dir (src)
        srcid = req.params.get("src")
        try:
            src = tree.getNode(srcid)
        except:
            req.writeTAL(
                "web/edit/edit.html", {"edit_action_error": srcid}, macro="edit_action_error")
            return

    if req.params.get('action') == 'addcontainer':
        node = tree.getNode(srcid)
        if not access.hasWriteAccess(node):
            # deliver errorlabel
            req.writeTALstr(
                '<tal:block i18n:translate="edit_nopermission"/>', {})
            return
        # create new container
        newnode_type = req.params.get('type')
        if newnode_type in ['bare_collection', 'bare_directory']:
            newnode_type = newnode_type.replace('bare_', '')

        translated_label = t(lang(req), 'edit_add_' + newnode_type)
        if translated_label.startswith('edit_add_'):
            translated_label = t(
                lang(req), 'edit_add_container_default') + newnode_type

        newnode = node.addChild(
            tree.Node(name=translated_label, type=newnode_type))
        newnode.set("creator", user.getName())
        newnode.set("creationtime", ustr(
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        req.params["dest"] = newnode.id

        # try:
        #    label = newnode.getLabel()
        # except:
        #    label = newnode.getName()
        #

        # c = len(newnode.getContentChildren())
        # if c>0:
        #    label += ' <small>(%s)</small>' %(c)

        label = getTreeLabel(newnode, lang=language)

        fancytree_nodedata = {
            'title': label,
            'key': newnode.id,
            'isLazy': False,
            'isFolder': True,
            'icon': getEditorIconPath(newnode),
            'readonly': 0,
            'tooltip': '%s (%s)' % (label, newnode.id),
            'children': [],
        }

        req.write(json.dumps(fancytree_nodedata))
        logg.info("%s adding new container %s (%s) to %s (%s, %s)", 
                  access.user.name, newnode.id, newnode.type, node.id, node.name, node.type)
        return

    try:
        destid = req.params.get("dest", None)
        dest = tree.getNode(destid)
        folderid = destid
    except:
        destid = None
        dest = None
        folderid = srcid

    idlist = getIDs(req)
    mysrc = None
    errorobj = None

    # try:
    if action == "clear_trash":
        for n in trashdir.getChildren():
            # if trashdir is it's sole parent, remove file from disk
            # attn: this will not touch files from children of deleted
            # containers
            if len(n.getParents()) == 1:
                logg.info("%s going to remove files from disk for node %s (%s, %s)", user.name, n.id, n.name, n.type)
                for f in n.getFiles():
                    # dangerous ??? check this
                    f_path = f.retrieveFile()
                    if os.path.exists(f_path):
                        logg.info("%s going to remove file %r from disk", user.name, f_path)
                        os.remove(f_path)
            trashdir.removeChild(n)
            dest = trashdir
        changednodes[trashdir.id] = 1
        _parent_descr = [(p.name, p.id, p.type) for p in trashdir_parents]
        logg.info("%s cleared trash folder with id %s, child of %s", user.name, trashdir.id, _parent_descr)
        # return
    else:
        for id in idlist:
            obj = tree.getNode(id)
            mysrc = src

            if isDirectory(obj):
                mysrc = obj.getParents()[0]

            if action == "delete":
                if access.hasWriteAccess(mysrc) and access.hasWriteAccess(obj):
                    if mysrc.id != trashdir.id:
                        mysrc.removeChild(obj)
                        changednodes[mysrc.id] = 1
                        trashdir.addChild(obj)
                        changednodes[trashdir.id] = 1
                        logg.info("%s moved to trash bin %s (%s, %s) from %s (%s, %s)",
                                  user.name, obj.id, obj.name, obj.type, mysrc.id, mysrc.name, mysrc.type)
                        dest = mysrc

                else:
                    logg.info("%s has no write access for node %s", user.name, mysrc.id)
                    req.writeTALstr(
                        '<tal:block i18n:translate="edit_nopermission"/>', {})
                dest = mysrc

            elif action in ["move", "copy"]:

                if dest != mysrc and \
                   access.hasWriteAccess(mysrc) and \
                   access.hasWriteAccess(dest) and \
                   access.hasWriteAccess(obj) and \
                   isDirectory(dest):
                    if not nodeIsChildOfNode(dest, obj):
                        if action == "move":
                            mysrc.removeChild(obj)
                            changednodes[mysrc.id] = 1  # getLabel(mysrc)
                        dest.addChild(obj)
                        changednodes[dest.id] = 1  # getLabel(dest)

                        if logg.isEnabledFor(logging.INFO):
                            _what = "%s %s %r (%s, %s) " % (
                                access.user.name, action, obj.id, obj.name, obj.type)
                            _from = "from %s (%s, %s) " % (
                                mysrc.id, mysrc.name, mysrc.type)
                            _to = "to %s (%s, %s)" % (
                                dest.id, dest.name, dest.type)
                            logg.info(_what + _from + _to)

                    else:
                        logg.error("%s could not %s %s from %s to %s", user.name, action, obj.id, mysrc.id, dest.id)
                else:
                    return
                mysrc = None

    if not mysrc:
        mysrc = src

    if action in ["move", "copy", "delete", "clear_trash"]:

        for nid in changednodes:
            try:
                changednodes[nid] = getTreeLabel(
                    tree.getNode(nid), lang=language)
            except:
                logg.exception("exception ignored: could not make fancytree label for node %s", nid)
        res_dict = {'changednodes': changednodes}
        req.write(json.dumps(res_dict, indent=4))
    else:
        try:
            req.write(dest.id)
        except:
            req.write('no-node-id-specified (web.edit.edit.action)')
            logg.exception('exception ignored, no-node-id-specified (web.edit.edit.action)')
    return


def showPaging(req, tab, ids):
    nodelist = req.session.get("nodelist", None)
    nextid = previd = None
    position = absitems = '&nbsp;'
    combodata = ""
    script = ""
    if nodelist and len(ids) == 1:
        previd = nodelist.getPrevious(ids[0])
        nextid = nodelist.getNext(ids[0])
        position, absitems = nodelist.getPositionString(ids[0])
        combodata, script = nodelist.getPositionCombo(tab)
    v = {"nextid": nextid, "previd": previd, "position": position, "absitems":
         absitems, "tab": tab, "combodata": combodata, "script": script, "nodeid": ids[0]}
    return req.getTAL("web/edit/edit.html", v, macro="edit_paging")


@dec_entry_log
def content(req):

    user = users.getUserFromRequest(req)

    access = AccessData(req)
    language = lang(req)
    if not access.user.isEditor():
        return req.writeTAL("web/edit/edit.html", {}, macro="error")

    if 'id' in req.params and len(req.params) == 1:
        nid = long(req.params.get('id'))
        node = q(Data).get(nid)

        if node is not None:
            cmd = "cd (%s %r, %r)" % (nid, node.name, node.type)
            logg.info("%s: %s", user.name, cmd)
        else:
            cmd = "ERROR-cd to non-existing id=%r" % nid
            logg.error("%s: %s", user.name, cmd)

    if 'action' in req.params and req.params['action'] == 'upload':
        pass

    content = {'script': '', 'body': ''}
    v = {'dircontent': '', 'notdirectory': 0, 'operations': ''}
    try:
        v['nodeiconpath'] = getEditorIconPath(node)
    except:
        v['nodeiconpath'] = "webtree/directory.gif"

    path = req.path[1:].split("/")
    if len(path) >= 4:
        req.params["style"] = "popup"
        req.params["id"] = path[1]
        req.params["tab"] = path[2]
        req.params["option"] = path[3]
    getEditModules()

    if not access.user.isEditor():
        return req.writeTAL("web/edit/edit.html", {}, macro="error")

    # remove all caches for the frontend area- we might make changes there
    for sessionkey in ["contentarea", "navframe"]:
        try:
            del req.session[sessionkey]
        except:
            pass

    ids = getIDs(req)

    if req.params.get("type", "") == "help" and req.params.get("tab", "") == "upload":
        return upload_help(req)

    if len(ids) > 0:
        node = q(Node).get(long(ids[0]))
    tabs = "content"
    if node.type == "root":
        tabs = "content"
    elif node.id == users.getUploadDir(access.getUser()).id:
        tabs = "upload"
    elif node.id == users.getImportDir(access.getUser()).id:
        tabs = "imports"
    elif hasattr(node, "getDefaultEditTab"):
        tabs = node.getDefaultEditTab()
        v["notdirectory"] = 0

    current = req.params.get("tab", tabs)
    logg.debug("... %s inside %s.%s: ->  !!! current = %s !!!", get_user_id(req), __name__, funcname(), current)
    msg = "%s selected editor module is %s" % (user.name, current)
    jsfunc = req.params.get("func", "")
    if jsfunc:
        msg = msg + (', js-function: %r' % jsfunc)
    logg.info(msg)

    # some tabs operate on only one file
    # if current in ["files", "view", "upload"]:
    if current in ["files", "upload"]:
        ids = ids[0:1]

    # display current images
    if not isinstance(q(Data).get(ids[0]), Container):
        v["notdirectory"] = 1
        items = []
        if current != "view":
            for id in ids:
                node = q(Data).get(id)
                if hasattr(node, "show_node_image"):
                    if not isDirectory(node) and not node.isContainer():
                        items.append((id, node.show_node_image()))
                    else:
                        items.append(("", node.show_node_image()))
        v["items"] = items
        if logg.isEnabledFor(logging.DEBUG):
            logg.debug("... %s inside %s.%s: -> display current images: items: %s", 
                       get_user_id(req), __name__, funcname(), [_t[0] for _t in items])
        try:
            n = q(Data).get(req.params.get('src', req.params.get('id')))
            if current == 'metadata' and 'save' in req.params:
                pass
            s = []
            while n:
                try:
                    s = ['<a onClick="activateEditorTreeNode(%r); return false;" href="/edit/edit_content?id=%s">%s</a>' %
                         (n.id, n.id, n.getLabel(lang=language))] + s
                except:
                    s = ['<a onClick="activateEditorTreeNode(%r); return false;" href="/edit/edit_content?id=%s">%s</a>' %
                         (n.id, n.id, n.name)] + s

                p = n.getParents()
                if p:
                    n = p[0]
                else:
                    n = None
            v["dircontent"] = ' <b>&raquo;</b> '.join(s[1:])
        except:
            logg.exception('ERROR displaying current images, exception ignored')

    else:  # or current directory
        n = q(Data).get(long(ids[0]))
        s = []
        while n:
            if len(s) == 0:
                try:
                    s = ['%s' % (n.getLabel(lang=language))]
                except:
                    s = ['%s' % (n.name)]
            else:
                try:
                    s = ['<a onClick="activateEditorTreeNode(%r); return false;" href="/edit/edit_content?id=%s">%s</a>' %
                         (n.id, n.id, n.getLabel(lang=language))] + s
                except:
                    s = ['<a onClick="activateEditorTreeNode(%r); return false;" href="/edit/edit_content?id=%s">%s</a>' %
                         (n.id, n.id, n.name)] + s

            p = n.getParents()
            if p:
                n = p[0]
            else:
                n = None
        v["dircontent"] = ' <b>&raquo;</b> '.join(s[1:])

    if current == "globals":
        basedir = config.get("paths.datadir")
        file_to_edit = None

        if "file_to_edit" in req.params:
            file_to_edit = req.params["file_to_edit"]

        if not file_to_edit:
            d = node.getStartpageDict()
            if d and lang(req) in d:
                file_to_edit = d[lang(req)]

        found = False
        for f in node.getFiles():
            if f.mimetype == 'text/html':
                filepath = f.retrieveFile().replace(basedir, '')
                if file_to_edit == filepath:
                    found = True
                    # XXX. dead code?
                    result = edit_editor(req, node, f)
                    if result == "error":
                        logg.error("error editing %s", f.retrieveFile())
                    break

        if not found:
            edit_editor(req, node, None)

    # XXX. dead code?
    elif current == "tab_metadata":
        edit_metadata(req, ids)  # undefined
    elif current == "tab_upload":
        edit_upload(req, ids)  # undefined
    elif current == "tab_import":
        edit_import(req, ids)  # undefined
    elif current == "tab_globals":
        req.write("")
    elif current == "tab_lza":
        edit_lza(req, ids)  # undefined
    elif current == "tab_logo":
        edit_logo(req, ids)  # undefined
    else:
        t = current.split("_")[-1]
        if t in editModules.keys():
            c = editModules[t].getContent(req, ids)
            if c:
                content["body"] += c  # use standard method of module
            else:
                logg.debug('empty content')
                return
        else:
            req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
            content["body"] += req.getTAL("web/edit/edit.html", {"module": current}, macro="module_error")

    if req.params.get("style", "") != "popup":  # normal page with header
        v["tabs"] = handletabs(req, ids, tabs)
        v["script"] = content["script"]
        v["body"] = content["body"]
        v["paging"] = showPaging(req, current, ids)
        v["node"] = node
        v["ids"] = req.params.get("ids", "").split(",")
        if req.params.get("ids", "") == "":
            v["ids"] = req.params.get("id", "").split(",")
        v["tab"] = current
        v["operations"] = req.getTAL("web/edit/edit_common.html", {'iscontainer': node.isContainer()}, macro="show_operations")
        user = users.getUserFromRequest(req)
        v['user'] = user
        v['language'] = lang(req)
        v['t'] = translation_t

        v['spc'] = [Menu("sub_header_frontend", "../", target="_parent")]
        if user.isAdmin():
            v['spc'].append(Menu("sub_header_administration", "../admin", target="_parent"))

        if user.isWorkflowEditor():
            v['spc'].append(Menu("sub_header_workflow", "../publish", target="_parent"))

        v['spc'].append(Menu("sub_header_logout", "../logout", target="_parent"))

        # add icons to breadcrumbs
        ipath = 'webtree/directory.gif'
        if node and node.isContainer():
            if node.name == 'home' or 'Arbeitsverzeichnis' in node.name:
                ipath = 'webtree/homeicon.gif'
            elif node.name == 'Uploads':
                ipath = 'webtree/uploadicon.gif'
            elif node.name == 'Importe':
                ipath = 'webtree/importicon.gif'
            elif node.name == 'Inkonsistente Daten':
                ipath = 'webtree/faultyicon.gif'
            elif node.name == 'Papierkorb':
                ipath = 'webtree/trashicon.gif'
            else:
                ipath = getEditorIconPath(node)

        v["dircontent"] += '&nbsp;&nbsp;<img src="' + '/img/' + ipath + '" />'

        return req.writeTAL("web/edit/edit.html", v, macro="frame_content")


def printmethod(req):
    getEditModules()
    if req.params.get("module") in editModules.keys():
        mod = editModules[req.params.get("module")]
        return mod.getPrintView(req)
