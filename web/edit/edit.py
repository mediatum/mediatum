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
import re
import time
import urllib
import json
import traceback
import core.tree as tree
import core.config as config
import core.help as help
import core.users as users
import core.usergroups as usergroups
import core.translation
import utils.log
import logging
from core.acl import AccessData
from utils.utils import Link, isCollection, Menu, getFormatedString, splitpath, parseMenuString, isDirectory

from edit_common import *

from core.translation import lang
from core.translation import t as translation_t

from core.transition import httpstatus

from edit_common import EditorNodeList
from core.datatypes import loadAllDatatypes, Datatype
from core.tree import getRoot, remove_from_nodecaches
from schema.schema import loadTypesFromDB
from utils.utils import funcname, get_user_id, log_func_entry, dec_entry_log

from pprint import pprint as pp, pformat as pf

logger = logging.getLogger('editor')


containertypes = []


def clearFromCache(node):
    if node is tree.getRoot('collections'):
        return
    for n in node.getAllChildren():
        remove_from_nodecaches(n)


def getContainerTreeTypes(req):
    '''
    function only called to fill context menues for editor tree
    '''
    global containertypes
    containertypes = []

    def getDatatypes(req):
        dtypes = []
        for scheme in AccessData(req).filter(loadTypesFromDB()):
            dtypes += scheme.getDatatypes()
        return set(dtypes)

    if 1:  # len(containertypes)==0:
        dtypes = getDatatypes(req)

        for dtype in loadAllDatatypes():
            if dtype.name in dtypes:
                n = tree.Node("", type=dtype.name)
                if hasattr(n, "isContainer") and hasattr(n, "isSystemType"):
                    if n.isContainer() and not n.isSystemType():
                        if dtype not in containertypes:
                            containertypes.append(dtype)

    ct_names = [ct.name for ct in containertypes]
    # Datatype(key, key, cls.__name__, cls.__module__+'.'+cls.__name__)
    for key in ['collection', 'directory']:
        prefix = 'bare_'
        # user should be able to create collection and directory containers to
        # have a functinal system. in a completly empty mediatum there will be no
        # metadatatypes (schemata) for those. they are inserted here on-the-fly
        # as bare_collection, bare_directory
        if key not in ct_names:
            containertypes.append(Datatype(prefix + key, prefix + key, 'no_class',
                                           'generated on-the-fly for editor to provide name for context_menue'))

    return containertypes


def getContainerTreeTypes_orig(req):
    def getDatatypes(req):
        dtypes = []
        for scheme in AccessData(req).filter(loadTypesFromDB()):
            dtypes += scheme.getDatatypes()
        return set(dtypes)

    if len(containertypes) == 0:
        dtypes = getDatatypes(req)

        for dtype in loadAllDatatypes():
            if dtype.name in dtypes:
                n = tree.Node("", type=dtype.name)
                if hasattr(n, "isContainer") and hasattr(n, "isSystemType"):
                    if n.isContainer() and not n.isSystemType():
                        containertypes.append(dtype)
    return containertypes


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
    id = req.params.get("id", tree.getRoot("collections").id)
    tab = req.params.get("tab", None)
    language = lang(req)

    access = AccessData(req)
    if not access.getUser().isEditor():
        req.writeTAL("web/edit/edit.html", {}, macro="error")
        req.writeTAL("web/edit/edit.html",
                     {"id": id, "tab": (tab and "&tab=" + tab) or ""}, macro="edit_notree_permission")
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return

    try:
        currentdir = tree.getNode(id)
    except tree.NoSuchNodeError:
        currentdir = tree.getRoot("collections")
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
    containerpath = [('%s' % p.id) for p in nodepath if p.isContainer()]

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

    cmenu = sorted(getContainerTreeTypes(req), key=lambda x: x.getName())
    cmenu_iconpaths = []

    for ct in cmenu:
        ct_name = ct.getName()
        _n = tree.Node("", type=ct_name)
        # translations of ct_name will be offered in editor tree context menu
        cmenu_iconpaths.append(
            [ct, getEditorIconPath(_n), ct_name, translation_t(language, ct_name)])

    # a html snippet may be inserted in the editor header
    header_insert = tree.getRoot('collections').get('system.editor.header.insert.' + language).strip()
    help_link = tree.getRoot('collections').get('system.editor.help.link.' + language).strip()
    homenodefilter = req.params.get('homenodefilter', '')

    v = {
        "id": id,
        "tab": (tab and "&tab=" + tab) or "",
        'user': user,
        'spc': spc,
        'folders': folders,
        'collectionsid': tree.getRoot('collections').id,
        "basedirs": [tree.getRoot('home'), tree.getRoot('collections')],
        'cmenu': cmenu,
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

    n = tree.getNode(ids[0])
    if n.type.startswith("workflow"):
        n = tree.getRoot()

    menu = filterMenu(getEditMenuString(n.getContentType()), user)

    spc = [Menu("sub_header_frontend", "../", target="_parent")]
    if user.isAdmin():
        spc.append(
            Menu("sub_header_administration", "../admin", target="_parent"))

    if user.isWorkflowEditor():
        spc.append(Menu("sub_header_workflow", "../publish", target="_parent"))

    spc.append(Menu("sub_header_logout", "../logout", target="_parent"))

    # a html snippet may be inserted in the editor header
    help_link = tree.getRoot('collections').get('system.editor.help.link.' + language).strip()
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
                    try:
                        path, module = splitpath(modpath[1])
                        if modpath[0] == '':
                            m = __import__("web.edit.modules." + name[:-3])
                            m = eval("m.edit.modules." + name[:-3])
                        else:
                            sys.path += [path]
                            m = __import__(
                                module.replace("/", ".") + "." + name[:-3])
                            m = eval("m." + name[:-3])
                        editModules[name[:-3]] = m
                    except ImportError as e:
                        print e
                        logger.error("import error in module " + name[:-3])
                    except SyntaxError:
                        logger.error("syntax error in module " + name[:-3])
                        print sys.exc_info()

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
        nodes = core.tree.getRoot(
            'collections').getContainerChildren().sort_by_orderpos()
    elif req.params.get('key') == 'home':
        if not user.isAdmin():
            nodes = [home_dir]
        else:
            homenodefilter = req.params.get('homenodefilter', '')
            if homenodefilter:
                nodes = []
                try:
                    pattern = re.compile(homenodefilter)
                    nodes = tree.getRoot('home').getContainerChildren().sort_by_orderpos()
                    # filter out shoppingbags etc.
                    nodes = [n for n in nodes if n.isContainer()]
                    # filter user name - after first "("
                    nodes = filter(lambda n: re.match(homenodefilter, n.getLabel(language).split('(', 1)[-1]), nodes)
                    match_result = '#=%d' % len(nodes)
                except Exception as e:
                    logger.warning('pattern matching for home nodes: %r' % e)
                    match_result = '<span style="color:red">Error: %r</span>' % str(e)
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

    for dtype in loadAllDatatypes():  # all known datatypes
        if dtype.name == ntype:
            n = tree.Node("", type=dtype.name)
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
                msg = "could not make fancytree label for node %r" % nid
                logger.error(msg)
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
        newnode.set("creationtime", str(
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        clearFromCache(node)
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
        msg = "%s adding new container %r (%r) to %r (%r, %r)" % (
            access.user.name, newnode.id, newnode.type, node.id, node.name, node.type)
        logging.getLogger('usertracing').info(msg)
        logger.info(msg)
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
                logger.info("%s going to remove files from disk for node %r (%r, %r)" % (
                    user.getName(), n.id, n.name, n.type))
                for f in n.getFiles():
                    # dangerous ??? check this
                    f_path = f.retrieveFile()
                    if os.path.exists(f_path):
                        logger.info(
                            "%s going to remove file %r from disk" % (user.getName(), f_path))
                        os.remove(f_path)
            trashdir.removeChild(n)
            dest = trashdir
        clearFromCache(trashdir)
        changednodes[trashdir.id] = 1
        _parent_descr = [(p.name, p.id, p.type) for p in trashdir_parents]
        msg = "%s cleared trash folder with id %s, child of %r" % (
            user.getName(), trashdir.id, _parent_descr)
        logger.info(msg)
        logging.getLogger('usertracing').info(msg)
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
                        clearFromCache(mysrc)
                        logger.info("%s moved to trash bin %s (%r, %r) from %s (%r, %r)" % (
                            user.getName(), obj.id, obj.name, obj.type, mysrc.id, mysrc.name, mysrc.type))
                        logging.getLogger('usertracing').info("%s removed %s (%r, %r) from %s (%r, %r)" % (
                            user.getName(), obj.id, obj.name, obj.type, mysrc.id, mysrc.name, mysrc.type))
                        dest = mysrc

                else:
                    logger.info(
                        "%s has no write access for node %s" % (user.getName(), mysrc.id))
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
                        clearFromCache(dest)

                        _what = "%s %s %r (%r, %r) " % (
                            access.user.name, action, obj.id, obj.name, obj.type)
                        _from = "from %r (%r, %r) " % (
                            mysrc.id, mysrc.name, mysrc.type)
                        _to = "to %r (%r, %r)" % (
                            dest.id, dest.name, dest.type)
                        msg = _what + _from + _to
                        logging.getLogger('usertracing').info(msg)
                        logger.info(msg)

                    else:
                        logger.error("%s could not %s %s from %s to %s" % (
                            user.getName(), action, obj.id, mysrc.id, dest.id))
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
                msg = "could not make fancytree label for node %r" % nid
                logger.error(msg)
        res_dict = {'changednodes': changednodes}
        req.write(json.dumps(res_dict, indent=4))
    else:
        try:
            req.write(dest.id)
        except:
            req.write('no-node-id-specified (web.edit.edit.action)')
            logger.warning('no-node-id-specified (web.edit.edit.action)')
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
        nid = req.params.get('id')
        try:
            node = tree.getNode(nid)
        except:
            node = None
        if node:
            cmd = "cd (%s %r, %r)" % (nid, node.name, node.type)
            logger.info("%s: %s" % (user.getName(), cmd))
            #logging.getLogger("usertracing").info("%s: in editor %s" % (user.getName(), cmd))
        else:
            cmd = "ERROR-cd to non-existing id=%r" % nid
            logger.error("%s: %s") % (user.getName(), cmd)

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
        node = tree.getNode(ids[0])
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
    logger.debug("... %s inside %s.%s: ->  !!! current = %r !!!" %
                 (get_user_id(req), __name__, funcname(), current))
    msg = "%s selected editor module is %r" % (user.getName(), current)
    jsfunc = req.params.get("func", "")
    if jsfunc:
        msg = msg + (', js-function: %r' % jsfunc)
    logger.info(msg)

    # some tabs operate on only one file
    # if current in ["files", "view", "upload"]:
    if current in ["files", "upload"]:
        ids = ids[0:1]

    # display current images
    if not tree.getNode(ids[0]).isContainer():
        v["notdirectory"] = 1
        items = []
        if current != "view":
            for id in ids:
                node = tree.getNode(id)
                if hasattr(node, "show_node_image"):
                    if not isDirectory(node) and not node.isContainer():
                        items.append((id, node.show_node_image()))
                    else:
                        items.append(("", node.show_node_image()))
        v["items"] = items
        logger.debug("... %s inside %s.%s: -> display current images: items: %r" %
                     (get_user_id(req), __name__, funcname(), [_t[0] for _t in items]))
        try:
            n = tree.getNode(req.params.get('src', req.params.get('id')))
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
            logger.exception('ERROR displaying current images')

    else:  # or current directory
        n = tree.getNode(ids[0])
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
                    result = edit_editor(req, node, f)
                    if result == "error":
                        logger.error("error editing %r" % f.retrieveFile())
                    break

        if not found:
            edit_editor(req, node, None)

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
                logger.debug('empty content')
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
