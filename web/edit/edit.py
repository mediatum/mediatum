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
from core import Node, NodeType, db, User, UserGroup, UserToUserGroup
from core.systemtypes import Metadatatypes
from core.database.postgres.permission import NodeToAccessRuleset, AccessRulesetToRule, AccessRule

from contenttypes import Container, Collections, Data, Home

from core.translation import lang, t
from edit_common import *
from core.transition import httpstatus, current_user

from utils.utils import funcname, get_user_id, dec_entry_log, Menu, splitpath, parseMenuString,\
    isDirectory, isCollection
from schema.schema import Metadatatype
from web.edit.edit_common import get_edit_label


logg = logging.getLogger(__name__)
q = db.query


def getTreeLabel(node, lang):
    label = get_edit_label(node, lang)
    c = node.content_children.count()
    if c > 0:
        label += ' <small>(%s)</small>' % (c)
    return label


def getEditorIconPath(node, req=None):
    '''
    retrieve icon path for editor tree relative to img/
    '''
    if req:
        user = current_user

        if node is user.home_dir:
            return 'webtree/homeicon.gif'
        elif node is user.upload_dir:
            return 'webtree/uploadicon.gif'
        elif node is user.trash_dir:
            return 'webtree/trashicon.gif'

    if hasattr(node, 'treeiconclass'):
        return "webtree/" + node.treeiconclass() + ".gif"
    else:
        return "webtree/" + node.type + ".gif"


def get_editor_icon_path_from_nodeclass(cls):
    '''
    retrieve icon path for editor tree relative to img/
    '''

    if hasattr(cls, 'treeiconclass'):
        return u"webtree/{}.gif".format(cls.treeiconclass())
    else:
        return u"webtree/{}.gif".format(cls.__name__)


def getIDPaths(nid, sep="/", containers_only=True):
    '''
    return list of sep-separated id lists for paths to node with id nid
    '''
    try:
        node = q(Node).get(nid)
        if not node.has_read_access():
            return []
    except:
        return []
    from web.frontend.content import getPaths
    paths = getPaths(node)
    res = []
    for path in paths:
        if containers_only:
            pids = [("%s" % p.id)
                    for p in path if isinstance(p, Container)]
        else:
            pids = [("%s" % p.id) for p in path]
        if pids:
            res.append(sep.join(pids))
    return res


def frameset(req):
    id = req.params.get("id", q(Collections).one().id)
    tab = req.params.get("tab", None)
    language = lang(req)
    user = current_user

    if not user.is_editor:
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

    # use always the newest version
    currentdir = currentdir.getActiveVersion()

    if unicode(currentdir.id) != id:
        req.params["id"] = unicode(currentdir.id)
        id = req.params.get("id")

    nodepath = []
    n = currentdir
    while n:
        nodepath = [n] + nodepath
        p = n.parents
        if p:
            n = p[0]
        else:
            n = None

    path = ['%s' % p.id for p in nodepath]
    containerpath = [('%s' % p.id) for p in nodepath if isinstance(p, Container)]

    spc = [Menu("sub_header_frontend", "../", target="_parent")]
    if user.is_admin:
        spc.append(
            Menu("sub_header_administration", "../admin", target="_parent"))

    if user.is_workflow_editor:
        spc.append(Menu("sub_header_workflow", "../publish/", target="_parent"))

    spc.append(Menu("sub_header_logout", "../logout", target="_parent"))

    def getPathToFolder(node):
        n = node
        path = []
        while n:
            path = ['/%s' % n.id] + path
            p = n.parents
            if p:
                n = p[0]
            else:
                n = None
        return (node, "".join(path[2:]))

    def _getIDPath(nid, sep="/", containers_only=True):
        res = getIDPaths(nid, sep=sep, containers_only=containers_only)
        return res

    # does the user have a homedir? if not, create one
    if user.home_dir is None:
        user.create_home_dir()
        db.session.commit()
        logg.info("created new home dir for user #%s (%s)", user.id, user.login_name)

    folders = {'homedir': getPathToFolder(user.home_dir),
               'trashdir': getPathToFolder(user.trash_dir),
               'uploaddir': getPathToFolder(user.upload_dir)}

    containertypes = Container.get_all_subclasses(filter_classnames=("collections", "home", "container", "project"))

    if not user.is_admin:
        # search all metadatatypes which are container
        container_nodetype_names = [c.__name__.lower() for c in containertypes]
        allowed_container_metadatanames = [x[0] for x in q(Metadatatype.name)
                                                  .filter(Metadatatype.name.in_(container_nodetype_names)).filter_read_access()]

        # remove all elements from containertypes which names are not in container_metadatanames
        new_containertypes = []
        for ct in containertypes:
            ct_name = ct.__name__
            if ct_name.lower() in allowed_container_metadatanames:
                new_containertypes += [ct]
        containertypes = new_containertypes

    cmenu_iconpaths = []

    for ct in containertypes:
        ct_name = ct.__name__
        # translations of ct_name will be offered in editor tree context menu
        cmenu_iconpaths.append(
            [ct_name.lower(), t(language, ct_name), get_editor_icon_path_from_nodeclass(ct)])

    # a html snippet may be inserted in the editor header
    # XXX: this should be moved to the settings table!
    header_insert, help_link = q(Collections.system_attrs[u"editor.header.insert" + language], 
                                 Collections.system_attrs[u"editor.help_link" + language]).one()
                                 
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
        't': t,
        '_getIDPath': _getIDPath,
        'system_editor_header_insert': (header_insert or "").strip(),
        'system_editor_help_link': (help_link or "").strip(),
        'homenodefilter': homenodefilter,
    }

    req.writeTAL("web/edit/edit.html", v, macro="edit_main")


def getBreadcrumbs(menulist, tab):
    for menuitem in menulist:
        for item in menuitem.getItemList():
            if item == tab or tab.startswith(item) or item.startswith(tab):
                return [menuitem.name, "*" + item]
    return [tab]


def filterMenu(menuitems, user):
    hide = user.hidden_edit_functions
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
    user = current_user
    language = lang(req)

    n = q(Data).get(ids[0])
    if n.type.startswith("workflow"):
        n = q(Root).one()

    menu = filterMenu(get_edit_menu_tabs(n.__class__), user)

    spc = [Menu("sub_header_frontend", "../", target="_parent")]
    if user.is_admin:
        spc.append(
            Menu("sub_header_administration", "../admin", target="_parent"))

    if user.is_workflow_editor:
        spc.append(Menu("sub_header_workflow", "../publish/", target="_parent"))

    spc.append(Menu("sub_header_logout", "../logout", target="_parent"))

    # a html snippet may be inserted in the editor header
    help_link = q(Collections.system_attrs['editor.help.link.' + language]).scalar()
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
            if os.path.isabs(modpath[1]):
                mod_dirpath = modpath[1]
            else:
                mod_dirpath = os.path.join(config.basedir, modpath[1])

            walk = os.walk(mod_dirpath)
            for dirpath, subdirs, files in walk:
                if os.path.basename(dirpath) not in ("test", "__pycache__"):
                    for name in [f for f in files if f.endswith(".py") and f != "__init__.py"]:
                        basename = name[:-3]
                        try:
                            path, module = splitpath(mod_dirpath)
                            if not modpath[0]:
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
            nodelist.append(q(Node).get(id))
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
        if not srcid:
            raise KeyError
        src = q(Node).get(srcid)
    except KeyError:
        src = None

    if type(ids) == str:
        idlist = ids.split(',')
    elif type(ids) == unicode:
        idlist = ids.split(u',')

    if idlist == [''] or idlist == [u'']:
        idlist = []
    return idlist


@dec_entry_log
def edit_tree(req):
    language = lang(req)
    user = current_user
    home_dir = user.home_dir
    match_result = ''
    match_error = False

    if req.params.get('key') == 'root':
        nodes = q(Collections).one().container_children.sort_by_orderpos()
    elif req.params.get('key') == 'home':
        if not user.is_admin:
            nodes = [home_dir]
        else:
            homenodefilter = req.params.get('homenodefilter', '')
            if homenodefilter:
                pattern = "%" + homenodefilter.strip() + "%"
                nodes = (q(Node).join(User, User.home_dir_id == Node.id)
                         .filter(User.login_name.ilike(pattern) | User.display_name.ilike(pattern)).all())
                if nodes:
                    match_result = u'#={}'.format(len(nodes))
                else:
                    match_result = u'<span style="color:red">Error: {} not found</span>'.format(homenodefilter)
                    match_error = True

                if home_dir not in nodes:
                    if not match_error:
                        match_result = u'#={}+1'.format(len(nodes))
                    nodes.insert(0, home_dir)
            else:
                nodes = [home_dir]
    else:
        nodes = q(Data).get(req.params.get('key')).container_children.sort_by_orderpos()
        nodes = [n for n in nodes if n.isContainer()]

    data = []

    for node in nodes:

        if not node.has_read_access():
            continue

        label = getTreeLabel(node, language)

        nodedata = {'title': label,
                    'key': node.id,
                    'lazy': True,
                    'folder': True,
                    'readonly': 0,
                    'tooltip': '%s (%s)' % (node.getLabel(lang=language), node.id),
                    'icon': getEditorIconPath(node, req)}

        if len(node.container_children) == 0:
            nodedata['lazy'] = False
            nodedata['children'] = []

        if not node.has_write_access():
            if req.params.get('key') == 'home':
                continue
            nodedata['readonly'] = 1
            nodedata['noLink'] = True

            nodedata['extraClasses'] = 'readonly'  # fancytree

        else:
            nodedata['readonly'] = 0

        if node is home_dir:
            nodedata["special_dir_type"] = "home"
            nodedata['match_result'] = match_result

        elif node is user.trash_dir:
            nodedata["special_dir_type"] = "trash"

        elif node is user.upload_dir:
            nodedata["special_dir_type"] = "upload"

        data.append(nodedata)

    return req.write(json.dumps(data, indent=4, ensure_ascii=False))


def get_edit_menu_tabs(nodeclass):
    root = q(Root).one()
    return root.system_attrs.get("edit.menu." + nodeclass.__name__.lower()) or nodeclass.get_default_edit_menu_tabs()


@dec_entry_log
def action(req):
    global editModules
    language = lang(req)
    user = current_user

    trashdir = user.trash_dir
    uploaddir = user.upload_dir

    trashdir_parents = trashdir.parents
    action = req.params.get("action", "")
    changednodes = {}

    if not user.is_editor:
        req.write("""permission denied""")
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return

    if "tab" in req.params:
        tab = req.params.get("tab").split("_")[-1]
        return editModules[tab].getContent(req, [req.params.get("id")])

    if action == "getlabels":
        nids = req.params.get('ids', [])
        nids = [nid.strip() for nid in nids.split(',') if nid.strip()]

        for nid in set(nids + [_n.id for _n in [trashdir, uploaddir]]):
            try:
                changednodes[nid] = getTreeLabel(q(Node).get(nid), language)
            except:
                logg.exception("exception ignored: could not make fancytree label for node %s", nid)
        res_dict = {'changednodes': changednodes}
        req.write(json.dumps(res_dict, indent=4, ensure_ascii=False))
        return

    else:
        # all 'action's except 'getlabels' require a base dir (src)
        # but expanding of a subdir in the edit-tree via fancytree has
        # not a srcid, so no action is necessary
        srcid = req.params.get("src")
        if not srcid:
            return
        try:
            src = q(Node).get(srcid)
        except:
            req.writeTAL(
                "web/edit/edit.html", {"edit_action_error": srcid}, macro="edit_action_error")
            return

    if req.params.get('action') == 'addcontainer':
        node = q(Node).get(srcid)
        if not node.has_write_access():
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

        content_class = Node.get_class_for_typestring(newnode_type)
        newnode = content_class(name=translated_label)
        node.children.append(newnode)
        newnode.set("creator", user.login_name)
        newnode.set("creationtime", unicode(
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        newnode.set("nodename", translated_label)  # set attribute named "nodename" to label text
        db.session.commit()
        req.params["dest"] = newnode.id

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

        req.write(json.dumps(fancytree_nodedata, ensure_ascii=False))
        logg.info("%s adding new container %s (%s) to %s (%s, %s)",
                  user.login_name, newnode.id, newnode.type, node.id, node.name, node.type)
        return

    try:
        destid = req.params.get("dest", None)
        dest = q(Node).get(destid)
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
        for n in trashdir.children:
            # if trashdir is it's sole parent, remove file from disk
            # attn: this will not touch files from children of deleted
            # containers
            if len(n.parents) == 1:
                logg.info("%s going to remove files from disk for node %s (%s, %s)", user.login_name, n.id, n.name, n.type)
                for f in n.files:
                    # dangerous ??? check this
                    f_path = f.abspath
                    if os.path.exists(f_path):
                        logg.info("%s going to remove file %r from disk", user.login_name, f_path)
                        os.remove(f_path)
            trashdir.children.remove(n)
            db.session.commit()
            dest = trashdir
        changednodes[trashdir.id] = 1
        _parent_descr = [(p.name, p.id, p.type) for p in trashdir_parents]
        logg.info("%s cleared trash folder with id %s, child of %s", user.login_name, trashdir.id, _parent_descr)
        # return
    else:
        for id in idlist:
            obj = q(Node).get(id)
            mysrc = src

            if isDirectory(obj) or isCollection(obj):
                mysrc = obj.parents[0]

            if action == "delete":
                if mysrc.has_write_access() and obj.has_write_access():
                    if mysrc.id != trashdir.id:
                        mysrc.children.remove(obj)
                        changednodes[mysrc.id] = 1
                        trashdir.children.append(obj)
                        db.session.commit()
                        changednodes[trashdir.id] = 1
                        logg.info("%s moved to trash bin %s (%s, %s) from %s (%s, %s)",
                                  user.login_name, obj.id, obj.name, obj.type, mysrc.id, mysrc.name, mysrc.type)
                        dest = mysrc

                else:
                    logg.info("%s has no write access for node %s", user.login_name, mysrc.id)
                    req.writeTALstr(
                        '<tal:block i18n:translate="edit_nopermission"/>', {})
                dest = mysrc

            elif action in ["move", "copy"]:

                if dest != (mysrc and
                            mysrc.has_write_access() and
                            dest.has_write_access() and
                            obj.has_write_access() and
                            isDirectory(dest)):
                    if not dest.is_descendant_of(obj):
                        if action == "move":
                            mysrc.children.remove(obj)
                            changednodes[mysrc.id] = 1  # getLabel(mysrc)
                        dest.children.append(obj)
                        changednodes[dest.id] = 1  # getLabel(dest)
                        db.session.commit()

                        if logg.isEnabledFor(logging.INFO):
                            _what = "%s %s %r (%s, %s) " % (
                                user.login_name, action, obj.id, obj.name, obj.type)
                            _from = "from %s (%s, %s) " % (
                                mysrc.id, mysrc.name, mysrc.type)
                            _to = "to %s (%s, %s)" % (
                                dest.id, dest.name, dest.type)
                            logg.info(_what + _from + _to)

                    else:
                        logg.error("%s could not %s %s from %s to %s", user.login_name, action, obj.id, mysrc.id, dest.id)
                else:
                    return
                mysrc = None

    if not mysrc:
        mysrc = src

    if action in ["move", "copy", "delete", "clear_trash"]:

        for nid in changednodes:
            try:
                changednodes[nid] = getTreeLabel(
                    q(Node).get(nid), lang=language)
            except:
                logg.exception("exception ignored: could not make fancytree label for node %s", nid)
        res_dict = {'changednodes': changednodes}
        req.write(json.dumps(res_dict, indent=4, ensure_ascii=False))
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

    v = {"nextid": nextid,
         "previd": previd,
         "position": position,
         "absitems": absitems,
         "tab": tab,
         "combodata": combodata,
         "script": script,
         "nodeid": int(ids[0])}

    return req.getTAL("web/edit/edit.html", v, macro="edit_paging")


@dec_entry_log
def content(req):

    user = current_user
    language = lang(req)

    if not user.is_editor:
        return req.writeTAL("web/edit/edit.html", {}, macro="error")

    if 'id' in req.params and len(req.params) == 1:
        nid = long(req.params.get('id'))
        node = q(Data).get(nid)

        if node is not None:
            cmd = "cd (%s %r, %r)" % (nid, node.name, node.type)
            logg.info("%s: %s", user.login_name, cmd)
        else:
            cmd = "ERROR-cd to non-existing id=%r" % nid
            logg.error("%s: %s", user.login_name, cmd)

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

    if not user.is_editor:
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
    if isinstance(node, Root):
        tabs = "content"
    elif node is user.upload_dir:
        tabs = "upload"
    else:
        tabs = node.get_default_edit_tab()
        v["notdirectory"] = 0

    current = req.params.get("tab", tabs)
    logg.debug("... %s inside %s.%s: ->  !!! current = %s !!!", get_user_id(req), __name__, funcname(), current)
    msg = "%s selected editor module is %s" % (user.login_name, current)
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

        nid = req.params.get('src', req.params.get('id'))
        if nid is None:
            raise ValueError("invalid request, neither 'src' not 'id' parameter is set!")

        folders_only = False
        if nid.find(',') > 0:
            # more than one node selected
            # use the first one for activateEditorTreeNode
            # and display only folders
            nid = nid.split(',')[0]
            folders_only = True
        n = q(Data).get(nid)
        if current == 'metadata' and 'save' in req.params:
            pass
        s = []
        while n:
            if not folders_only:
                s = ['<a onClick="activateEditorTreeNode(%r); return false;" href="/edit/edit_content?id=%s">%s</a>' %
                     (n.id, n.id, get_edit_label(n, language))] + s

            folders_only = False;
            p = n.parents
            # XXX: we only check the first parent. This is wrong, how could be solve this? #
            first_parent = p[0]
            if isinstance(first_parent, Data) and first_parent.has_read_access():
                n = p[0]
            else:
                n = None
        v["dircontent"] = ' <b>&raquo;</b> '.join(s)

    else:  # or current directory
        n = q(Data).get(long(ids[0]))
        s = []
        while n:
            if len(s) == 0:
                s = ['%s' % (get_edit_label(n, language))]
            else:
                s = ['<a onClick="activateEditorTreeNode(%r); return false;" href="/edit/edit_content?id=%s">%s</a>' %
                     (n.id, n.id, get_edit_label(n, language))] + s

            p = n.parents
            if p and not isinstance(p[0], Root):
                n = p[0]
            else:
                n = None
        v["dircontent"] = ' <b>&raquo;</b> '.join(s)

    if current == "globals":
        basedir = config.get("paths.datadir")
        file_to_edit = None

        if "file_to_edit" in req.params:
            file_to_edit = req.params["file_to_edit"]

        if not file_to_edit:
            # todo: getstartpagedict doesnt exist
            d = node.getStartpageDict()
            if d and language in d:
                file_to_edit = d[language]

        found = False
        for f in node.files:
            if f.mimetype == 'text/html':
                filepath = f.abspath.replace(basedir, '')
                if file_to_edit == filepath:
                    found = True
                    break

    else:
        t2 = current.split("_")[-1]
        if t2 in editModules.keys():
            c = editModules[t2].getContent(req, ids)

            if isinstance(c, int):
                # module returned a custom http status code instead of HTML content
                return c

            elif c:
                content["body"] += c
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
        v['user'] = user
        v['language'] = lang(req)
        v['t'] = t

        v['spc'] = [Menu("sub_header_frontend", "../", target="_parent")]
        if user.is_admin:
            v['spc'].append(Menu("sub_header_administration", "../admin", target="_parent"))

        if user.is_workflow_editor:
            v['spc'].append(Menu("sub_header_workflow", "../publish/", target="_parent"))

        v['spc'].append(Menu("sub_header_logout", "../logout", target="_parent"))

        # add icons to breadcrumbs
        ipath = 'webtree/directory.gif'
        if node and node.isContainer():
            if node.name == 'home' or 'Arbeitsverzeichnis' in node.name or node == current_user.home_dir:
                ipath = 'webtree/homeicon.gif'
            elif node.name in ('Uploads', 'upload'):
                ipath = 'webtree/uploadicon.gif'
            elif node.name in ('Papierkorb', 'trash'):
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
