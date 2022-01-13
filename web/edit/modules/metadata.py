# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from utils.date import format_date, parse_date, now
from utils.utils import funcname
from core import httpstatus
from core import Node, db
from contenttypes import Container
from core.users import user_from_session
import core.config as _core_config
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
    user = user_from_session()
    userdir = user.home_dir
    flag_nodename_changed = -1
    form = req.form

    for node in nodes:
        if not node.has_write_access() or node is userdir:
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if hasattr(mask, "i_am_not_a_mask"):
        for field in mask.metaFields():
            logg.debug("in %s.%s: (hasattr(mask,'i_am_not_a_mask')) field: %s, field.id: %s, field.name: %s, mask: %s, maskname: %s",
                __name__, funcname(), field, field.id, field.name, mask, mask.name)
            field_name = field.name
            if field_name == 'nodename' and mask.name == 'settings':
                if '__nodename' in form:
                    field_name = '__nodename'  # no multilang here !
                elif '{}__nodename'.format(_core_config.languages[0]) in form:
                    # no multilang here !
                    field_name = '{}__nodename'.format(_core_config.languages[0])
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
        db.session.commit()
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
        if (len(nodes) == 1 or old_nodename != new_nodename) and isinstance(nodes[0], Container):
            # for updates of node label in editor tree
            flag_nodename_changed = ustr(nodes[0].id)

    return flag_nodename_changed


def getContent(req, ids):
    ret = ""
    user = user_from_session()

    if "metadata" in user.hidden_edit_functions:
        logg.error("edit function is hidden")
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

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
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

        schema = node.schema
        if schema not in metatypes:
            metatypes.append(schema)
        if len(nodes) == 0 or nodes[0].schema == schema:
            nodes += [node]

    idstr = ",".join(ids)

    logg.info("%s in editor metadata: %r", user.login_name, [[n.id, n.name, n.type]for n in nodes])
    if len(ids) > 1 and len(metatypes) > 1:
        logg.info("%s user error: multiple metatypes in editor not supported", user.login_name)
        return _tal.processTAL({}, file="web/edit/modules/metadata.html", macro="multiple_documents_not_supported", request=req)

    metadatatype = node.metadatatype

    if metadatatype:
        for m in metadatatype.filter_masks(masktype='edit'):
            if m.has_read_access():
                masklist.append(m)

    if hasattr(node, "metaFields"):

        masklist = [SystemMask(
                "settings",
                _core_translation.t(req, "settings"),
                node.metaFields(_core_translation.set_language(req.accept_languages)),
            )] + masklist

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
        return _tal.processTAL({}, file="web/edit/modules/metadata.html", macro="no_mask", request=req)

    # context default for TAL interpreter
    ctx = dict(
            user=user,
            metatypes=metatypes,
            idstr=idstr,
            node=nodes[0],  # ?
            flag_nodename_changed=flag_nodename_changed,
            nodes=nodes,
            masklist=masklist,
            maskname=maskname,
            language=_core_translation.set_language(req.accept_languages),
            t=_core_translation.t,
            csrf=_core_csrfform.get_token(),
        )

    if "edit_metadata" in req.params:
        flag_nodename_changed = _handle_edit_metadata(req, mask, nodes)
        logg.debug("%s change metadata %s", user.login_name, idstr)
        logg.debug("%r", req.params)

    if "edit_metadata" in req.params or node.system_attrs.get("faulty") == "true":
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    update_date, creation_date = get_datelists(nodes)
    data = {}
    
    data["creation_date"] = creation_date
    data["update_date"] = update_date
    data["err"] = err

    _maskform, _fields = get_maskform_and_fields(nodes, mask, req)
    data["maskform"] = _maskform
    data["fields"] = _fields

    data.update(ctx)
    data["flag_nodename_changed"] = flag_nodename_changed
    data["srcnodeid"] = req.values.get("srcnodeid", "")

    ret += _tal.processTAL(data, file="web/edit/modules/metadata.html", macro="edit_metadata", request=req)
    return ret
