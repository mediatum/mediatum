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
from core.acl import AccessData
from core.db import database

import core.users as users
import core.tree as tree
import logging

from utils.date import format_date, parse_date, now
from utils.utils import formatException, funcname, get_user_id, log_func_entry, dec_entry_log
from core.translation import lang, t, getDefaultLanguage
from pprint import pprint as pp, pformat as pf
from core.transition import httpstatus

db = database.getConnection()

logger = logging.getLogger('editor')


def get_datelists(nodes):
    '''
    helper funtion to update default context before calling TAL interpreter
    '''
    update_date = []
    if len(nodes) == 1:
        for node in nodes:
            if node.get("updatetime"):
                try:
                    date = parse_date(
                        node.get("updatetime"), "%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.get("updatetime")
                update_date.append([node.get("updateuser"), datestr])

    creation_date = []
    if len(nodes) == 1:
        for node in nodes:
            if node.get("creationtime"):
                try:
                    date = parse_date(
                        node.get("creationtime"), "%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.get("creationtime")
                creation_date.append([node.get("creator"), datestr])

    return update_date, creation_date


def get_maskform_and_fields(nodes, mask, req):
    '''
    helper funtion to update default context before calling TAL interpreter
    '''
    if not hasattr(mask, "i_am_not_a_mask"):
        _maskform = mask.getFormHTML(nodes, req)
        _fields = None
    else:
        _maskform = None
        _fields = mask.metaFields()
    return _maskform, _fields


@dec_entry_log
def getContent(req, ids):
    ret = ""
    user = users.getUserFromRequest(req)

    if "metadata" in users.getHideMenusForUser(user):
        print "error 1"
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    access = AccessData(req)
    faultydir = users.getFaultyDir(user)
    metatypes = []
    nodes = []
    masklist = []
    err = 0

    # flag indicating change of node.name (fancytree node may have to be updated)
    # keep as integer
    # negative -> no change
    # else -> id of changed node
    flag_nodename_changed = -1

    for id in ids:
        node = tree.getNode(id)
        if not access.hasWriteAccess(node):
            print "error 2"
            req.setStatus(httpstatus.HTTP_FORBIDDEN)
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        schema = node.getSchema()
        if schema not in metatypes:
            metatypes.append(schema)
        if len(nodes) == 0 or nodes[0].getSchema() == schema:
            nodes += [node]

    idstr = ",".join(ids)
    action = req.params.get('action', '').strip()

    logger.info("%s in editor metadata (action=%r): %r" %
                (user.getName(), action, [[n.id, n.name, n.type]for n in nodes]))

    for m in node.getType().getMasks(type="edit"):
        if access.hasReadAccess(m):
            masklist.append(m)

    if hasattr(node, "metaFields"):

        class SystemMask:

            def __init__(self, name, description, fields):
                self.name, self.description, self.fields = name, description, fields

            def getName(self):
                return self.name

            def getDescription(self):
                return self.description

            def getDefaultMask(self):
                return False

            def metaFields(self, lang=None):
                return self.fields

            def i_am_not_a_mask():
                pass
        masklist = [SystemMask(
            "settings", t(req, "settings"), node.metaFields(lang(req)))] + masklist

    default = None
    for m in masklist:
        if m.getDefaultMask():
            default = m
            break
    if not default and len(masklist):
        default = masklist[0]

    maskname = req.params.get("mask", node.get("edit.lastmask") or "editmask")
    if maskname == "":
        maskname = default.getName()

    mask = None
    for m in masklist:
        if maskname == m.getName():
            mask = m
            break

    if not mask and default:
        mask = default
        maskname = default.getName()

    for n in nodes:
        n.set("edit.lastmask", maskname)

    if not mask:
        return req.getTAL("web/edit/modules/metadata.html", {}, macro="no_mask")

    # context default for TAL interpreter
    ctx = {}
    ctx["user"] = user
    ctx["access"] = access
    ctx["metatypes"] = metatypes
    ctx["idstr"] = idstr
    ctx["node"] = nodes[0]  # ?
    ctx["flag_nodename_changed"] = flag_nodename_changed
    ctx["nodes"] = nodes
    ctx["masklist"] = masklist
    ctx["maskname"] = maskname
    ctx["language"] = lang(req)
    ctx["t"] = t

    if action == 'restore':
        vid = req.params.get('vid', '0')
        node = nodes[0].getActiveVersion()
        if (vid != '0' and vid != node.id):
            n = tree.getNode(vid)
            # Not active version
            if n.next_nid != '0':

                next = tree.getNode(n.next_nid)
                if next.prev_nid != '0':
                    next.removeChild(tree.getNode(next.prev_nid))
                next.setPrevID(n.prev_nid)

                if n.prev_nid != '0':
                    prev = tree.getNode(n.prev_nid)
                    prev.setNextID(n.next_nid)
                    n.removeChild(prev)
                    next.addChild(prev)
                node.setNextID(n.id)

                n.setPrevID(node.id)
                n.setNextID('0')

                for pid in db.getParents(node.id):
                    parentNode = tree.getNode(pid)
                    parentNode.addChild(n)
                    parentNode.removeChild(node)
                n.addChild(node)

                nodes = [n]
                ids = [n.id]

                node_versions = nodes[0].getVersionList()
                update_date, creation_date = get_datelists(nodes)

                data = {'url': '?id=' + n.id + '&tab=metadata', 'pid':
                        None, 'flag_nodename_changed': flag_nodename_changed}

                data["versions"] = node_versions
                data["creation_date"] = creation_date
                data["update_date"] = update_date

                _maskform, _fields = get_maskform_and_fields(nodes, mask, req)
                data["maskform"] = _maskform
                data["fields"] = _fields

                data.update(ctx)

                return req.getTAL("web/edit/modules/metadata.html", data, macro="redirect")

    if action == 'delete':
        vid = req.params.get('vid', '0')
        if (vid != '0'):
            node = nodes[0].getActiveVersion()
            n = tree.getNode(vid)

            if (vid != node.id):
                n.set("deleted", "true")
                for pid in db.getParents(n.id):
                    parentNode = tree.getNode(pid)
                    parentNode.removeChild(n)
                for cid in db.getChildren(n.id):
                    n.removeChild(tree.getNode(cid))
                if n.next_nid != '0' and n.prev_nid != '0':
                    _next = tree.getNode(n.next_nid)
                    _next.addChild(tree.getNode(n.prev_nid))

                if n.next_nid != '0':
                    _next = tree.getNode(n.next_nid)
                    if n.prev_nid != '0':
                        _next.setPrevID(n.prev_nid)

                if n.prev_nid != '0':
                    _prev = tree.getNode(n.prev_nid)
                    if n.next_nid != '0':
                        _prev.setNextID(n.next_nid)
            else:
                pids = db.getParents(n.id)

                # Active version
                prev = None
                if n.prev_nid != '0':
                    prev = tree.getNode(n.prev_nid)
                    while prev.prev_nid != None and prev.prev_nid != '0' and prev.get("deleted") == "true":
                        prev = tree.getNode(prev.prev_nid)

                if prev != None and prev.get("deleted") != "true":
                    prev.setNextID('0')
                    for pid in pids:
                        parentNode = tree.getNode(pid)
                        parentNode.addChild(prev)
                    nodes = [prev]
                    ids = [prev.id]
                    n.set("deleted", "true")
                    for pid in pids:
                        parentNode = tree.getNode(pid)
                        parentNode.removeChild(n)

                    for cid in db.getChildren(n.id):
                        n.removeChild(tree.getNode(cid))

                    if n.next_nid != '0' and n.prev_nid != '0':
                        _next = tree.getNode(n.next_nid)
                        _next.addChild(tree.getNode(n.prev_nid))

                    node_versions = nodes[0].getVersionList()
                    update_date, creation_date = get_datelists(nodes)

                    data = {'url': '?id=' + prev.id + '&tab=metadata', 'pid':
                            None, 'flag_nodename_changed': flag_nodename_changed}

                    data["versions"] = node_versions
                    data["creation_date"] = creation_date
                    data["update_date"] = update_date

                    _maskform, _fields = get_maskform_and_fields(
                        nodes, mask, req)
                    data["maskform"] = _maskform
                    data["fields"] = _fields

                    data.update(ctx)

                    return req.getTAL("web/edit/modules/metadata.html", data, macro="redirect")
                else:
                    # Version 0
                    # Move node to trash
                    trashdir = users.getTrashDir(user)
                    trashdir.addChild(n)
                    for pid in pids:
                        parentNode = tree.getNode(pid)
                        parentNode.removeChild(n)

                    node_versions = nodes[0].getVersionList()
                    update_date, creation_date = get_datelists(nodes)

                    data = {'url': '?id=' + pids[0] + '&tab=content', 'pid': pids[
                        0], 'flag_nodename_changed': flag_nodename_changed}

                    data["versions"] = node_versions
                    data["creation_date"] = creation_date
                    data["update_date"] = update_date

                    _maskform, _fields = get_maskform_and_fields(
                        nodes, mask, req)
                    data["maskform"] = _maskform
                    data["fields"] = _fields

                    data.update(ctx)

                    return req.getTAL("web/edit/modules/metadata.html", data, macro="redirect")

    if "edit_metadata" in req.params:
        # check and save items
        userdir = users.getHomeDir(users.getUserFromRequest(req))

        for node in nodes:
            if not access.hasWriteAccess(node) or node.id == userdir.id:
                print "error 3"
                req.setStatus(httpstatus.HTTP_FORBIDDEN)
                return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        logging.getLogger('usertracing').info(
            access.user.name + " change metadata " + idstr)
        logging.getLogger('editor').info(
            access.user.name + " change metadata " + idstr)
        logging.getLogger('editor').debug(pf(req.params))

        for node in nodes:
            node.set("updateuser", user.getName())
            if node.get('updatetime') < str(now()):
                node.set("updatetime", str(format_date()))

        if not hasattr(mask, "i_am_not_a_mask"):
            if (req.params.get('generate_new_version')):
                # Create new node version
                _ids = []
                _nodes = []
                for node in nodes:
                    n = node.createNewVersion(user)
                    n.set("system.version.comment", '(' + t(req, "document_new_version_comment") +
                          ')\n' + req.params.get('version_comment', ''))

                    # add all existing attributes to the new version node
                    for attr, value in node.items():
                        # do not overwrite existing attributes
                        # do not copy system attributes
                        if n.get(attr) != "" or attr.startswith("system."):
                            pass
                        else:
                            n.set(attr, value)

                    _nodes.append(n)
                    _ids.append(n.id)

                ids = _ids
                idstr = ",".join(ids)
                nodes = _nodes
                nodes = mask.updateNode(nodes, req)

                node_versions = nodes[0].getVersionList()
                update_date, creation_date = get_datelists(nodes)

                data = {
                    'url': '?id=' + nodes[0].id + '&tab=metadata',
                    'pid': None,
                }

                data["versions"] = node_versions
                data["creation_date"] = creation_date
                data["update_date"] = update_date

                _maskform, _fields = get_maskform_and_fields(
                    nodes, mask, req)
                data["maskform"] = _maskform
                data["fields"] = _fields

                data.update(ctx)

                ret += req.getTAL("web/edit/modules/metadata.html",
                                  data, macro="redirect")
            else:
                if nodes:
                    old_nodename = nodes[0].name
                nodes = mask.updateNode(nodes, req)
                if nodes:
                    new_nodename = nodes[0].name
                    if (old_nodename != new_nodename) and hasattr(nodes[0], 'isContainer') and nodes[0].isContainer():
                        # for updates of node label in editor tree
                        flag_nodename_changed = str(node.id)

        else:
            for field in mask.metaFields():
                msg = "in %s.%s: (hasattr(mask,'i_am_not_a_mask')) field: %r, field.id: %r, field.name: %r, mask: %r, maskname: %r" % (
                    __name__, funcname(), field, field.id, field.getName(), mask, maskname)
                logger.debug(msg)
                field_name = field.getName()

                if field_name == 'nodename' and maskname == 'settings':
                    if '__nodename' in req.params:
                        field_name = '__nodename'  # no multilang here !
                    elif getDefaultLanguage() + '__nodename' in req.params:
                        # no multilang here !
                        field_name = getDefaultLanguage() + '__nodename'
                    value = req.params.get(field_name, None)
                    if value:
                        if value != node.name:
                            flag_nodename_changed = str(node.id)
                        for node in nodes:
                            node.setName(value)
                elif field_name in ('repec.code', 'repec.provider') and maskname == 'settings':
                    if '__' + field_name in req.params:
                        field_name = '__' + field_name  # no multilang here!
                    elif getDefaultLanguage() + '__' + field_name in req.params:
                        field_name = getDefaultLanguage() + '__' + field_name  # no multilang here!

                value = req.params.get(field_name, None)

                if value is not None:
                    for node in nodes:
                        node.set(field.getName(), value)
                else:
                    node.set(field.getName(), "")

    if "edit_metadata" in req.params or node.get("faulty") == "true":
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    node_versions = nodes[0].getVersionList()
    update_date, creation_date = get_datelists(nodes)

    data = {}
    data["versions"] = node_versions
    data["creation_date"] = creation_date
    data["update_date"] = update_date
    data["err"] = err

    _maskform, _fields = get_maskform_and_fields(nodes, mask, req)
    data["maskform"] = _maskform
    data["fields"] = _fields

    data.update(ctx)
    data["flag_nodename_changed"] = flag_nodename_changed

    ret += req.getTAL("web/edit/modules/metadata.html",
                      data, macro="edit_metadata")
    return ret
