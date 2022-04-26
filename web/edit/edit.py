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
from __future__ import division
from __future__ import print_function

import sys
import os
import re
import time
import json
import core.config as config
import core.translation
import mediatumtal.tal as _tal
import web.edit.edit_common as _web_edit_edit_common
import core.systemtypes as _core_systemtypes
import utils.utils as _utils_utils
from core import Node, NodeType, db, User, UserGroup, UserToUserGroup
from core.database.postgres.permission import NodeToAccessRuleset, AccessRulesetToRule, AccessRule

from contenttypes import Container, Collections, Data, Home

from core.translation import lang, t
from edit_common import *

from core.users import user_from_session as _user_from_session
from core import httpstatus
from schema.schema import Metadatatype
from web.edit.edit_common import get_edit_label, get_searchparams
from web.frontend.search import NoSearchResult
from utils.pathutils import get_accessible_paths
import web.common.pagination as _web_common_pagination
import web.common.sort as _sort

logg = logging.getLogger(__name__)
q = db.query


def getTreeLabel(node, lang):
    label = get_edit_label(node, lang)
    return label


def getEditorIconPath(node, home_dir = None, upload_dir = None, trash_dir = None):
    '''
    retrieve icon path for editor tree relative to img/
    '''

    if node is home_dir:
        return 'webtree/homeicon.gif'
    if node is upload_dir:
        return 'webtree/uploadicon.gif'
    if node is trash_dir:
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
    paths = get_accessible_paths(node)
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

def get_searchitems(req):
    searchitems = ''
    searchparams = get_searchparams(req)
    for k in searchparams:
        searchitems = '&' + k + '=' + searchparams[k]
    return searchitems

def frameset(req):
    user = _user_from_session()
    if not user.is_editor:
        data = _tal.processTAL({}, file="web/edit/edit.html", macro="error", request=req)
        data += _tal.processTAL({}, file="web/edit/edit.html", macro="edit_notree_permission", request=req)
        req.response.set_data(data)
        req.response.mimetype = "text/html"
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return

    language = lang(req)
    id = req.values.get("id", q(Collections).one().id)
    currentdir = q(Data).get(id)
    if currentdir is None:
        req.response.status_code = httpstatus.HTTP_NOT_FOUND
        req.response.set_data(t(language, "error_msg_objectnotfound"))
        return

    if not currentdir.has_read_access():
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        req.response.set_data(t(language, "permission_denied"))
        return

    page = int(req.values.get("page", 1))
    nodes_per_page = req.values.get("nodes_per_page", "")
    if nodes_per_page:
        nodes_per_page = int(nodes_per_page)
    sortfield = req.values.get("sortfield", "")
    value = req.values.get("value", "")
    tab = req.values.get("tab")

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

    spc = [_utils_utils.Menu("sub_header_frontend", "../", target="_parent")]
    if user.is_admin:
        spc.append(
            _utils_utils.Menu("sub_header_administration", "../admin", target="_parent"))

    if user.is_workflow_editor:
        spc.append(_utils_utils.Menu("sub_header_workflow", "../publish/", target="_parent"))

    spc.append(_utils_utils.Menu("sub_header_help", "http://mediatum.readthedocs.io", target="_blank"))

    spc.append(_utils_utils.Menu("sub_header_logout", "../logout", target="_parent"))

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

    folders = dict(
            homedir=getPathToFolder(user.home_dir),
            trashdir=getPathToFolder(user.trash_dir),
            uploaddir=getPathToFolder(user.upload_dir),
        )

    containertypes = Container.get_all_subclasses(filter_classnames=("collections", "home", "container"))

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

    homenodefilter = req.values.get('homenodefilter', '')

    req.response.status_code = httpstatus.HTTP_OK
    req.response.set_data(_tal.processTAL(
            dict(
                id=id,
                page=page,
                nodes_per_page=nodes_per_page,
                sortfield=sortfield,
                value=value,
                searchitems=get_searchitems(req),
                tab="&tab={}".format(tab) if tab else "",
                user=user,
                spc=spc,
                folders=folders,
                collectionsid=q(Collections).one().id,
                basedirs=[q(Home).one(), q(Collections).one()],
                cmenu_iconpaths=cmenu_iconpaths,
                path=path,
                containerpath=containerpath,
                language=lang(req),
                t=t,
                _getIDPath=_getIDPath,
                homenodefilter=homenodefilter,
                csrf=req.csrf_token.current_token,
            ),
            file="web/edit/edit.html",
            macro="edit_main",
            request=req,
        ),
    )


def getBreadcrumbs(menulist, tab):
    for menuitem in menulist:
        for item in menuitem.getItemList():
            if item == tab or tab.startswith(item.name) or item.name.startswith(tab):
                return [menuitem.name, "*" + item.name]
    return [tab]

def _handletabs(req, ids, tabs, sort_choices):
    user = _user_from_session()

    n = q(Data).get(ids[0])
    if n.type.startswith("workflow"):
        n = q(_core_systemtypes.Root).one()

    menu = _utils_utils.parse_menu_struct(n.editor_menu, lambda mi: mi not in user.hidden_edit_functions)
    nodes_per_page = req.args.get("nodes_per_page", type=int)
    if not nodes_per_page:
        nodes_per_page = 20
    sortfield = req.args.get("sortfield")

    if not sortfield:
        sortfield = n.get("sortfield")
        if sortfield.strip() == "":
            sortfield = "off"

    if sortfield.strip() not in ("", "off"):
        n.set("sortfield", sortfield)
    elif n.get("sortfield"):
        n.removeAttribute("sortfield")
    db.session.commit()

    return _tal.processTAL(
            dict(
                user=user,
                ids=ids,
                idstr=",".join(ids),
                srcnodeid=req.values.get('srcnodeid', ''),
                menu=menu,
                breadcrumbs=getBreadcrumbs(menu, req.values.get("tab", tabs)),
                sort_choices=sort_choices,
                sortfield=sortfield,
                nodes_per_page=nodes_per_page,
            ),
            file="web/edit/edit.html",
            macro="edit_tabs",
            request=req,
        )

def error(req):
    req.response.set_data(_tal.processTAL(
            dict(errormsg=req.values.get("errmsg", "")),
            string="<tal:block tal:replace=\"errormsg\"/>",
            macro="edit_errorpage",
            request=req,
        ),
    )
    req.response.status_code = httpstatus.HTTP_OK
    return httpstatus.HTTP_OK


# delivers all edit modules
_editModules = {}


def getEditModules():
    for modpath in core.editmodulepaths:  # paths with edit modules
        if os.path.isabs(modpath[1]):
            mod_dirpath = modpath[1]
        else:
            mod_dirpath = os.path.join(config.basedir, modpath[1])

        for dirpath, subdirs, files in os.walk(mod_dirpath):
            if os.path.basename(dirpath) in ("test", "__pycache__"):
                continue
            for name in files:
                if (not name.endswith(".py")) or (name == "__init__.py"):
                    continue
                basename,_ = os.path.splitext(name)
                with _utils_utils.suppress(ImportError,SyntaxError):
                    path, module = _utils_utils.splitpath(mod_dirpath)
                    if not modpath[0]:
                        m = __import__("web.edit.modules." + basename)
                        m = eval("m.edit.modules." + basename)
                    else:
                        sys.path += [path]
                        m = __import__(module.replace("/", ".") + "." + basename)
                        m = eval("m." + basename)
                    _editModules[basename] = m


def getIDs(req):
    # look for one "id" parameter, containing an id or a list of ids
    try:
        id = req.values["id"]
    except KeyError:
        pass
    else:
        idlist = id.split(",")
        if idlist != ['']:
            return idlist

    return req.values.getlist('ids')


def edit_tree(req):
    language = lang(req)
    user = _user_from_session()
    home_dir = user.home_dir
    upload_dir = user.upload_dir
    trash_dir = user.trash_dir
    match_result = ''
    match_error = False

    if req.values['key'] == 'root':
        nodes = q(Collections).one().container_children.sort_by_orderpos()
    elif req.values['key'] == 'home':
        if not user.is_admin:
            nodes = [home_dir]
        else:
            homenodefilter = req.values.get('homenodefilter', '')
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
        nodes = q(Data).get(req.values['key']).container_children.sort_by_orderpos()
        nodes = [n for n in nodes if n.isContainer()]

    data = []

    for node in nodes:
        if not node.has_read_access():
            continue

        label = getTreeLabel(node, language)
        nodedata = dict(
                title=label,
                key=node.id,
                lazy=True,
                folder=True,
                readonly=0,
                tooltip=u'{} ({})'.format(node.getLabel(lang=language), node.id),
                icon=getEditorIconPath(node, home_dir=home_dir, upload_dir=upload_dir, trash_dir=trash_dir),
            )

        if len(node.container_children) == 0:
            nodedata['lazy'] = False
            nodedata['children'] = []

        if not node.has_write_access():
            if req.values['key'] == 'home':
                continue
            nodedata['readonly'] = 1
            nodedata['noLink'] = True
            nodedata['extraClasses'] = 'readonly'  # fancytree
        else:
            nodedata['readonly'] = 0

        if node is home_dir:
            nodedata["special_dir_type"] = "home"
            nodedata['match_result'] = match_result

        elif node is trash_dir:
            nodedata["special_dir_type"] = "trash"

        elif node is upload_dir:
            nodedata["special_dir_type"] = "upload"

        data.append(nodedata)

    req.response.status_code = httpstatus.HTTP_OK
    req.response.set_data(json.dumps(data, indent=4, ensure_ascii=False))


def action(req):
    language = lang(req)
    user = _user_from_session()
    if not user.is_editor:
        req.response.set_data(t(language, "permission_denied"))
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return

    if "tab" in req.values:
        nid = req.values.get("id")
        node = q(Node).get(nid)
        if not node:
            req.response.status_code = httpstatus.HTTP_NOT_FOUND
            req.response.set_data(t(language, "error_msg_objectnotfound"))
            return
        if not node.has_read_access():
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            req.response.set_data(t(language, "permission_denied"))
            return
        tab = req.values["tab"].split("_")[-1]
        return _editModules[tab].getContent(req, [nid])

    trashdir = user.trash_dir
    uploaddir = user.upload_dir
    trashdir_parents = trashdir.parents
    action = req.values["action"]
    changednodes = {}

    if action == "getlabels":
        nids = req.values['ids']
        nids = [nid.strip() for nid in nids.split(',') if nid.strip()]

        for nid in set(nids + [_n.id for _n in [trashdir, uploaddir]]):
            try:
                changednodes[nid] = getTreeLabel(q(Node).get(nid), language)
            except:
                logg.exception("exception ignored: could not make fancytree label for node %s", nid)
        req.response.status_code = httpstatus.HTTP_OK
        req.response.set_data(json.dumps(dict(changednodes=changednodes), indent=4, ensure_ascii=False))
        return
    else:
        # all 'action's except 'getlabels' require a base dir (src)
        # but expanding of a subdir in the edit-tree via fancytree has
        # not a srcnodeid, so no action is necessary
        srcnodeid = req.values.get("srcnodeid")
        if not srcnodeid:
            return
        try:
            srcnode = q(Node).get(srcnodeid)
        except:
            req.response.status_code = httpstatus.HTTP_OK
            req.response.set_data(_tal.processTAL(
                    dict(edit_action_error=srcnodeid),
                    file="web/edit/edit.html",
                    macro="edit_action_error",
                    request=req,
                ),
            )
            return

    if req.values['action'] == 'addcontainer':
        if not srcnode.has_write_access():
            # deliver errorlabel
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            req.response.set_data(_tal.processTAL(
                    {},
                    string='<tal:block i18n:translate="edit_nopermission"/>',
                    macro=None,
                    request=req,
                ),
            )
            return
        # create new container
        newnode_type = req.values['type']
        if newnode_type in ['bare_collection', 'bare_directory']:
            newnode_type = newnode_type.replace('bare_', '')

        translated_label = t(lang(req), 'edit_add_' + newnode_type)
        if translated_label.startswith('edit_add_'):
            translated_label = t(
                lang(req), 'edit_add_container_default') + newnode_type

        content_class = Node.get_class_for_typestring(newnode_type)
        newnode = content_class(name=translated_label)
        srcnode.children.append(newnode)
        newnode.set("creator", user.login_name)
        newnode.set("creationtime", unicode(
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
        newnode.set("nodename", translated_label)  # set attribute named "nodename" to label text
        # place newnode at top of the children by setting the orderpos to the lowest orderpos - 1
        # if the orderpos gets negative, shift the oderpos of all children by incrementing with a positive number
        # make this number large enough, to avoid the next shifting of orderpos if more containers are added
        if len(srcnode.children) == 1:
            # newnode is the only one child
            newnode.orderpos = 1000
        else:
            newnode.orderpos = srcnode.children[0].orderpos
            newnode.orderpos = min([c.orderpos for c in srcnode.children]) - 1
            while newnode.orderpos < 0:
                # in order to avoid negative orderpos, add a positive number to the orderpos of all children
                # make this number large enough, so there is no shift of orderpos is necessary if the next
                # container is added to the children
                for c in srcnode.children:
                    c.orderpos += 1000
        db.session.commit()

        label = getTreeLabel(newnode, lang=language)

        req.response.status_code = httpstatus.HTTP_OK
        req.response.set_data(json.dumps(
                dict(
                    title=label,
                    key=newnode.id,
                    isLazy=False,
                    isFolder=True,
                    icon=getEditorIconPath(newnode),
                    readonly=0,
                    tooltip=u'{} ({})'.format(label, newnode.id),
                    children=[],
                ),
                ensure_ascii=False,
            ),
        )
        logg.info("%s adding new container %s (%s) to %s (%s, %s)",
                  user.login_name, newnode.id, newnode.type, srcnode.id, srcnode.name, srcnode.type)
        return

    if action in ("move", "copy"):
        dest = q(Node).get(req.values["dest"])

    idlist = getIDs(req)

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
            mysrc = srcnode

            if _utils_utils.isDirectory(obj) or _utils_utils.isCollection(obj):
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
                else:
                    logg.info("%s has no write access for node %s", user.login_name, mysrc.id)
                    req.response.set_data(
                        req.response.get_data() +
                        _tal.processTAL(
                            {},
                            file='<tal:block i18n:translate="edit_nopermission"/>',
                            macro=None,
                            request=req,
                        ),
                    )
                dest = mysrc
            elif action in ["move", "copy"]:
                if (dest != mysrc) and \
                            mysrc.has_write_access() and \
                            dest.has_write_access() and \
                            obj.has_write_access() and \
                            isinstance(dest, Container):
                    if not dest.is_descendant_of(obj):
                        if action == "move":
                            mysrc.children.remove(obj)
                            changednodes[mysrc.id] = 1  # getLabel(mysrc)
                        dest.children.append(obj)
                        changednodes[dest.id] = 1  # getLabel(dest)
                        db.session.commit()

                        logg.info(
                            "%s %s %r (%s, %s) from %s (%s, %s) to %s (%s, %s)",
                            user.login_name,
                            action,
                            obj.id,
                            obj.name,
                            obj.type,
                            mysrc.id,
                            mysrc.name,
                            mysrc.type,
                            dest.id,
                            dest.name,
                            dest.type,
                        )
                    else:
                        logg.error("%s could not %s %s from %s to %s", user.login_name, action, obj.id, mysrc.id, dest.id)
                else:
                    return

    if action in ["move", "copy", "delete", "clear_trash"]:
        for nid in changednodes:
            try:
                changednodes[nid] = getTreeLabel(
                    q(Node).get(nid), lang=language)
            except:
                logg.exception("exception ignored: could not make fancytree label for node %s", nid)
        req.response.status_code = httpstatus.HTTP_OK
        req.response.set_data(json.dumps(dict(changednodes=changednodes), indent=4, ensure_ascii=False))
    else:
        try:
            req.response.status_code = httpstatus.HTTP_OK
            if dest is not None:
                req.response.set_data(dest.id)
            else:
                req.response.set_data('no-node-id-specified (web.edit.edit.action)')
        except:
            req.response.set_data('no-node-id-specified (web.edit.edit.action)')
            logg.exception('exception ignored, no-node-id-specified (web.edit.edit.action)')
    return


def showPaging(req, tab, ids):
    nodelist = None
    srcnodeid = req.values.get("srcnodeid")
    if srcnodeid:
        node = q(Node).get(srcnodeid)
        _show_dir_nav = _web_edit_edit_common.ShowDirNav(req)
        nodes = _show_dir_nav.get_children(node, req.values.get('sortfield'))
        nodelist = EditorNodeList(nodes)

    nextid = previd = None
    position = absitems = '&nbsp;'
    combodata = ""
    script = ""
    if nodelist and len(ids) == 1:
        previd = nodelist.getPrevious(ids[0])
        nextid = nodelist.getNext(ids[0])
        position, absitems = nodelist.getPositionString(ids[0])
        combodata, script = nodelist.getPositionCombo(tab)

    req.response.status_code = httpstatus.HTTP_OK
    return _tal.processTAL(
            dict(
                nextid=nextid,
                previd=previd,
                position=position,
                absitems=absitems,
                tab=tab,
                combodata=combodata,
                script=script,
                srcnodeid=srcnodeid,
                nodeid=int(ids[0]),
            ),
            file="web/edit/edit.html",
            macro="edit_paging",
            request=req,
        )


def content(req):
    user = _user_from_session()
    req.response.status_code = httpstatus.HTTP_OK
    if not user.is_editor:
        req.response.set_data(_tal.processTAL({}, file="web/edit/edit.html", macro="error", request=req))
        return

    if req.values.get("type", "") == "help" and req.values.get("tab", "") == "upload":
        return upload_help(req)

    if 'id' in req.values and len(req.values) == 1:
        nid = long(req.values['id'])
        node = q(Data).get(nid)
        if node is not None:
            cmd = "cd (%s %r, %r)" % (nid, node.name, node.type)
            logg.info("%s: %s", user.login_name, cmd)
        else:
            cmd = "ERROR-cd to non-existing id=%r" % nid
            logg.error("%s: %s", user.login_name, cmd)

    ids = getIDs(req)
    if len(ids) > 0:
        if ids[0] == "all":
            show_dir_nav = _web_edit_edit_common.ShowDirNav(req)
            ids = show_dir_nav.get_ids_from_req()
        node = q(Node).get(long(ids[0]))

    language = lang(req)
    if not node.has_read_access():
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        req.response.set_data(t(language, "permission_denied"))
        return

    if isinstance(node, _core_systemtypes.Root):
        tabs = "content"
    elif node is user.upload_dir:
        tabs = "upload"
    else:
        tabs = node.get_default_edit_tab()

    current = req.values.get("tab", tabs)
    # "_" was used as separator in tab name in early versions,
    # but is not permitted anymore:
    assert "_" not in tabs
    assert "_" not in current
    logg.debug("... %s inside %s.%s: ->  !!! current = %s !!!", _utils_utils.get_user_id(), __name__, _utils_utils.funcname(), current)
    msg = "%s selected editor module is %s" % (user.login_name, current)
    jsfunc = req.values.get("func", "")
    if jsfunc:
        msg = msg + (', js-function: %r' % jsfunc)
    logg.info("%s", msg)

    # some tabs operate on only one file
    # if current in ["files", "view", "upload"]:
    if current in ["files", "upload"]:
        ids = ids[0:1]

    v = dict()

    try:
        v['nodeiconpath'] = getEditorIconPath(node)
    except:
        v['nodeiconpath'] = "webtree/directory.gif"

    # display current images
    if not isinstance(q(Data).get(ids[0]), Container):
        v["notdirectory"] = 1
        items = []
        if current != "view":
            for id in ids:
                node = q(Data).get(id)
                if hasattr(node, "show_node_image"):
                    if not _utils_utils.isDirectory(node) and not node.isContainer():
                        items.append((id, node.show_node_image()))
                    else:
                        items.append(("", node.show_node_image()))
        v["items"] = items
        if logg.isEnabledFor(logging.DEBUG):
            logg.debug("... %s inside %s.%s: -> display current images: items: %s",
                       _utils_utils.get_user_id(), __name__, _utils_utils.funcname(), [_t[0] for _t in items])

        nid = req.values.get('srcnodeid', req.values.get('id'))
        if nid is None:
            raise ValueError("invalid request, neither 'srcnodeid' not 'id' parameter is set!")

        folders_only = False
        if nid.find(',') > 0:
            # more than one node selected
            # use the first one for activateEditorTreeNode
            # and display only folders
            nid = nid.split(',')[0]
            folders_only = True
        n = q(Data).get(nid)
        s = []
        path = list(next(iter(get_accessible_paths(n) or ((),))))
        if not folders_only:
            path.append(n)
        for p in path:
            s.append(
                     u"<a onClick='activateEditorTreeNode({id}); return true;'"
                     " href='/edit/edit_content?srcnodeid={id}&id={id}'>{label}</a>"
                     .format(id=p.id, label=get_edit_label(p, language))
                     )
        v["dircontent"] = ' <b>&raquo;</b> '.join(s)
    else:  # or current directory
        v["notdirectory"] = 0
        n = q(Data).get(long(ids[0]))
        s = []
        for p in next(iter(get_accessible_paths(n) or ((),))):
            s.append(
                     u"<a onClick='activateEditorTreeNode({id}); return true;'"
                     " href='/edit/edit_content?srcnodeid={id}&id={id}'>{label}</a>"
                     .format(id=p.id, label=get_edit_label(p, language))
                     )
        s.append(get_edit_label(n, language))
        v["dircontent"] = ' <b>&raquo;</b> '.join(s)

    if tabs == 'upload' and current == 'content':
        current = 'upload'

    if "globalsort" in req.values:
        node.set("sortfield", req.values["globalsort"])

    v['collection_sortfield'] = req.values.get("sortfield", node.get("sortfield"))

    if req.values.get("style") != "popup":
        if not isinstance(node, (_core_systemtypes.Root, Collections, Home)):
            sortchoices = tuple(_sort.get_sort_choices(
                    container=node,
                    off="off",
                    t_off=t(req, "off"),
                    t_desc=t(req, "descending"),
                ))
        else:
            sortchoices = ()

        v["tabs"] = _handletabs(req, ids, tabs, sortchoices)

    c = _editModules[current].getContent(req, ids)
    if not c:
        logg.debug('empty content')
        return
    if isinstance(c, int):
        # module returned a custom http status code instead of HTML content
        return c

    if req.values.get("style") == "popup":  # normal page with header
        return

    v.update(
            script="",
            body=c,
            paging=showPaging(req, current, ids),
            node=node,
            ids=(req.values.get("ids") or req.values.get("id", "")).split(","),
            tab=current,
            operations=_tal.processTAL(
                 dict(iscontainer=node.isContainer()),
                 file="web/edit/edit_common.html",
                 macro="show_operations",
                 request=req,
             ),
            user=user,
            language=lang(req),
            t=t,
           )

    # add icons to breadcrumbs
    ipath = 'webtree/directory.gif'
    if node and node.isContainer():
        if node.name == 'home' or 'Arbeitsverzeichnis' in node.name or node == user.home_dir:
            ipath = 'webtree/homeicon.gif'
        elif node.name in ('Uploads', 'upload'):
            ipath = 'webtree/uploadicon.gif'
        elif node.name in ('Papierkorb', 'trash'):
            ipath = 'webtree/trashicon.gif'
        else:
            ipath = getEditorIconPath(node)

    v["dircontent"] += '&nbsp;&nbsp;<img src="' + '/img/' + ipath + '" />'
    v["nodesperpage_options"] = _web_common_pagination.get_config_nodes_per_page(True)
    v["sortfield"] = v.get("collection_sortfield", req.values.get("sortfield", node.get("sortfield"))) or "off"
    v["nodesperpage_from_req"] = req.values.get("nodes_per_page")

    req.response.set_data(_tal.processTAL(v, file="web/edit/edit.html", macro="frame_content", request=req))


RE_EDIT_PRINT_URL = re.compile("/print/(\d+)_([a-z]+)(?:_(.+)?)?\.pdf")


def edit_print(req):
    match = RE_EDIT_PRINT_URL.match(req.mediatum_contextfree_path)
    nid = int(match.group(1))
    node = q(Node).get(nid)
    if not node:
        req.response.set_data(t(lang(req), "error_msg_objectnotfound"))
        return
    if not node.has_read_access():
        req.response.set_data(t(lang(req), "permission_denied"))
        return

    module_name = match.group(2)
    mod = _editModules.get(module_name)
    
    if not mod:
        req.response.status_code = httpstatus.HTTP_BAD_REQUEST
        req.response.set_data(t(lang(req), "admin_settings_nomodule"))
        return
        
    additional_data = match.group(3)
    print_content = mod.getPrintView(nid, additional_data, req)
    req.response.content_type = "application/pdf"
    req.response.headers['Content-Disposition'] = u'inline; filename="{}_{}_{}.pdf"'.format(nid, module_name,
                                                                                              additional_data)
    req.response.set_data(print_content)
    req.response.status_code = httpstatus.HTTP_OK
