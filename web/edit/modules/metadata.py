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
from core import db
from core.database.postgres.node import Node
from contenttypes import Container
from core.users import user_from_session
import core.config as _core_config
import datetime

q = db.query
logg = logging.getLogger(__name__)


def _get_datelists(nodes):
    '''
    helper funtion to update default context before calling TAL interpreter
    '''
    if len(nodes) != 1:
        return None, None
    node, = nodes

    update_date = None
    if node.updatetime:
        try:
            date = parse_date(
                node.updatetime, "%Y-%m-%dT%H:%M:%S")
            datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
        except:
            datestr = node.updatetime
        update_date = (node.get("updateuser"), datestr)

    creation_date = None
    if node.get("creationtime"):
        try:
            date = parse_date(
                node.get("creationtime"), "%Y-%m-%dT%H:%M:%S")
            datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
        except:
            datestr = node.get("creationtime")
        creation_date = (node.get("creator"), datestr)

    return update_date, creation_date


class _SystemMask:

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

    def i_am_not_a_mask(self):
        pass


def _handle_edit_metadata(req, mask, nodes):
    # check and save items
    user = user_from_session()
    userdir = user.home_dir
    flag_nodename_changed = -1
    form = req.form

    for node in nodes:
        assert node.has_write_access() and node is not userdir

    if not hasattr(mask, "i_am_not_a_mask"):
        # XXX: why check here?
        # if nodes:
        old_nodename = nodes[0].name

        attrs = mask.get_edit_update_attrs(req, user)
        for node in nodes:
            mask.apply_edit_update_attrs_to_node(node, attrs)

        # XXX: why check here?
        # if nodes:
        new_nodename = nodes[0].name
        if (len(nodes) == 1 or old_nodename != new_nodename) and isinstance(nodes[0], Container):
            # for updates of node label in editor tree
            flag_nodename_changed = ustr(nodes[0].id)
        db.session.commit()
        return flag_nodename_changed

    for field in mask.metaFields():
        logg.debug("in %s.%s: (hasattr(mask,'i_am_not_a_mask')) field: %s, field.id: %s, field.name: %s, mask: %s, maskname: %s",
            __name__, funcname(), field, field.id, field.name, mask, mask.name)
        field_name = field.name
        if field_name == 'nodename' and mask.name == 'settings':
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
    return flag_nodename_changed


def getContent(req, ids):
    ret = ""
    user = user_from_session()

    if "metadata" in user.hidden_edit_functions:
        logg.error("edit function is hidden")
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    err = 0

    # flag indicating change of node.name (fancytree node may have to be updated)
    # keep as integer
    # negative -> no change
    # else -> id of changed node
    flag_nodename_changed = -1

    nodes = map(q(Node).get, ids)

    if not all(node.has_write_access() for node in nodes):
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    logg.info("%s in editor metadata: %r", user.login_name, [[n.id, n.name, n.type]for n in nodes])

    if len(frozenset(node.schema for node in nodes))!=1:
        logg.info("%s user error: multiple metatypes in editor not supported", user.login_name)
        return _tal.processTAL({}, file="web/edit/modules/metadata.html", macro="multiple_documents_not_supported", request=req)

    idstr = ",".join(ids)

    masks = {}
    if hasattr(nodes[-1], "metaFields") and len(frozenset(node.type for node in nodes)) == 1:
        masks["settings"] = _SystemMask(
                "settings",
                _core_translation.translate_in_request("settings", req),
                nodes[-1].metaFields(_core_translation.set_language(req.accept_languages)),
               )

    metadatatype = nodes[-1].metadatatype
    if metadatatype:
        masks.update(**{
                mask.name:mask
                for mask in metadatatype.filter_masks(masktype='edit')
                if mask.has_read_access()
               })

    # default mask is first mask that claims to be default mask, or None
    default_mask = list(mask for mask in masks.itervalues() if mask.getDefaultMask())
    default_mask.append(None)
    default_mask = default_mask[0]

    mask = masks.get(
            req.values.get("mask", nodes[-1].system_attrs.get("edit.lastmask") or "editmask"),
            default_mask,
           )

    if not mask:
        return _tal.processTAL({}, file="web/edit/modules/metadata.html", macro="no_mask", request=req)

    # context default for TAL interpreter
    ctx = dict(
            user=user,
            idstr=idstr,
            node=nodes[0], # ?
            node_count=len(nodes),
            flag_nodename_changed=flag_nodename_changed,
            masklist=masks.values(),
            maskname=mask.name,
            language=_core_translation.set_language(req.accept_languages),
            translate=_core_translation.translate,
            csrf=_core_csrfform.get_token(),
        )

    if "edit_metadata" in req.params:
        if user.home_dir in nodes or not all(node.has_write_access() for node in nodes):
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

        flag_nodename_changed = _handle_edit_metadata(req, mask, nodes)
        logg.debug("%s change metadata %s", user.login_name, idstr)
        logg.debug("%r", req.params)
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    data = {}

    data["update_date"], data["creation_date"] = _get_datelists(nodes)
    data["err"] = err

    data["maskform"] = mask.getFormHTML(nodes, req) if not hasattr(mask, "i_am_not_a_mask") else None
    data["fields"] = mask.metaFields() if hasattr(mask, "i_am_not_a_mask") else None

    data.update(ctx)
    data["flag_nodename_changed"] = flag_nodename_changed
    data["srcnodeid"] = req.values.get("srcnodeid", "")

    ret += _tal.processTAL(data, file="web/edit/modules/metadata.html", macro="edit_metadata", request=req)
    return ret
