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

from utils.date import format_date, parse_date, now
from utils.utils import funcname, dec_entry_log
from core.translation import lang, t, getDefaultLanguage
from pprint import pformat as pf
from core.transition import httpstatus, current_user
from core import Node, db
from contenttypes import Container
from core.users import user_from_session
import datetime

q = db.query
logg = logging.getLogger(__name__)


def get_datelists(nodes):
    '''
    helper funtion to update default context before calling TAL interpreter
    '''
    update_date = []
    if len(nodes) == 1:
        for node in nodes:
            if node.updatetime:
                try:
                    date = parse_date(
                        node.updatetime, "%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.updatetime
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


def _handle_edit_metadata(req, mask, nodes):
    # check and save items
    user = current_user
    userdir = user.home_dir
    flag_nodename_changed = -1
    form = req.form

    for node in nodes:
        if not node.has_write_access() or node is userdir:
            req.setStatus(httpstatus.HTTP_FORBIDDEN)
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if not hasattr(mask, "i_am_not_a_mask"):
        if form.get('generate_new_version'):
            # Create new node version
            comment = u'({})\n{}'.format(t(req, "document_new_version_comment"), form.get('version_comment', ''))

            for node in nodes:
                with node.new_tagged_version(comment=comment, user=user):
                    mask.update_node(node, req, user)
        else:
            # XXX: why check here?
            # if nodes:
            old_nodename = nodes[0].name

            for node in nodes:
                mask.update_node(node, req, user)

            db.session.commit()

            # XXX: why check here?
            # if nodes:
            new_nodename = nodes[0].name
            if ( len(nodes) == 1 or old_nodename != new_nodename) and isinstance(nodes[0], Container):
                # for updates of node label in editor tree
                flag_nodename_changed = ustr(nodes[0].id)

    else:
        for field in mask.metaFields():
            logg.debug("in %s.%s: (hasattr(mask,'i_am_not_a_mask')) field: %s, field.id: %s, field.name: %s, mask: %s, maskname: %s",
                __name__, funcname(), field, field.id, field.name, mask, mask.name)
            field_name = field.name
            if field_name == 'nodename' and mask.name == 'settings':
                if '__nodename' in form:
                    field_name = '__nodename'  # no multilang here !
                elif getDefaultLanguage() + '__nodename' in form:
                    # no multilang here !
                    field_name = getDefaultLanguage() + '__nodename'
                value = form.get(field_name, None)
                if value:
                    if value != node.name:
                        flag_nodename_changed = ustr(node.id)
                    for node in nodes:
                        node.name = value
            value = form.get(field_name, None)
            if value is not None:
                for node in nodes:
                    node.set(field.name, value)
            else:
                node.set(field.getName(), "")

    return flag_nodename_changed


@dec_entry_log
def getContent(req, ids):
    ret = ""
    user = user_from_session(req.session)

    if "metadata" in user.hidden_edit_functions:
        print "error 1"
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    metatypes = []
    nodes = []
    masklist = []
    err = 0

    # flag indicating change of node.name (fancytree node may have to be updated)
    # keep as integer
    # negative -> no change
    # else -> id of changed node
    flag_nodename_changed = -1

    for nid in ids:
        node = q(Node).get(nid)
        if not node.has_write_access():
            req.setStatus(httpstatus.HTTP_FORBIDDEN)
            return req.getTAL("web/edit/edit.html", {}, macro="access_error")

        schema = node.schema
        if schema not in metatypes:
            metatypes.append(schema)
        if len(nodes) == 0 or nodes[0].schema == schema:
            nodes += [node]

    idstr = ",".join(ids)
    action = req.params.get('action', '').strip()

    if len(ids) > 1:
        logg.info("%s in editor metadata (action=%r) multiple documents not supported: %r",
                  user.login_name, action, [[n.id, n.name, n.type]for n in nodes])
        return req.getTAL("web/edit/modules/metadata.html", {}, macro="multiple_documents_not_supported")

    logg.info("%s in editor metadata (action=%r): %r", user.login_name, action, [[n.id, n.name, n.type]for n in nodes])

    metadatatype = node.metadatatype

    if metadatatype:
        for m in metadatatype.filter_masks(masktype='edit'):
            if m.has_read_access():
                masklist.append(m)

    if hasattr(node, "metaFields"):

        masklist = [SystemMask(
            "settings", t(req, "settings"), node.metaFields(lang(req)))] + masklist

    default = None
    for m in masklist:
        if m.getDefaultMask():
            default = m
            break
    if not default and len(masklist):
        default = masklist[0]

    maskname = req.params.get("mask", node.system_attrs.get("edit.lastmask") or "editmask")
    if maskname == "":
        maskname = default.name

    mask = None
    for m in masklist:
        if maskname == m.name:
            mask = m
            break

    if not mask and default:
        mask = default
        maskname = default.name

    for n in nodes:
        n.system_attrs["edit.lastmask"] = maskname

    db.session.commit()

    if not mask:
        return req.getTAL("web/edit/modules/metadata.html", {}, macro="no_mask")

    # context default for TAL interpreter
    ctx = {}
    ctx["user"] = user
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
        raise NotImplementedError("restore version not implemented, later...")

    if action == 'delete':
        raise NotImplementedError("delete version not implemented, later...")

    if "edit_metadata" in req.params:
        flag_nodename_changed = _handle_edit_metadata(req, mask, nodes)
        logg.debug("%s change metadata %s", user.login_name, idstr)
        logg.debug(pf(req.params))

    if "edit_metadata" in req.params or node.system_attrs.get("faulty") == "true":
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    update_date, creation_date = get_datelists(nodes)
    data = {}
    
    # version handling
    current_version = nodes[0].versions[-1]
    tagged_node_versions = nodes[0].tagged_versions.all()
    
    data["untagged_current_version"] = current_version

    if tagged_node_versions:
        data["tagged_versions"] = tagged_node_versions[::-1] # descending version tag
        if current_version == tagged_node_versions[-1]:
            data["untagged_current_version"] = None
    else:
        data["tagged_versions"] = []
        
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
