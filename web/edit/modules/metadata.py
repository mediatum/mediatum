# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import functools as _functools
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


def _get_name_date(date, name_getter):
    if not date:
        return
    try:
        date = parse_date("%Y-%m-%dT%H:%M:%S")
        datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
    except:
        datestr = date
    return (name_getter(), datestr)


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
    form = req.form

    for node in nodes:
        assert node.has_write_access() and node is not userdir

    if not hasattr(mask, "i_am_not_a_mask"):
        attrs = mask.get_edit_update_attrs(req, user)
        for node in nodes:
            mask.apply_edit_update_attrs_to_node(node, attrs)

        db.session.commit()
        return

    for field in mask.metaFields():
        logg.debug("in %s.%s: (hasattr(mask,'i_am_not_a_mask')) field: %s, field.id: %s, field.name: %s, mask: %s, maskname: %s",
            __name__, funcname(), field, field.id, field.name, mask, mask.name)
        field_name = field.name
        if field_name == 'nodename' and mask.name == 'settings':
            value = form.get(field_name, None)
            if value:
                for node in nodes:
                    node.name = value
        value = form.get(field_name, None)
        if value is not None:
            for node in nodes:
                node.set(field.name, value)
        else:
            node.set(field.getName(), "")

    db.session.commit()


def getContent(req, ids):
    user = user_from_session()

    if "metadata" in user.hidden_edit_functions:
        logg.error("edit function is hidden")
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    err = 0

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

    if "edit_metadata" in req.params:
        if user.home_dir in nodes or not all(node.has_write_access() for node in nodes) \
                or req.values.get("mask")!=mask.name:
            req.response.status_code = httpstatus.HTTP_FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

        _handle_edit_metadata(req, mask, nodes)
        logg.debug("%s change metadata %s", user.login_name, idstr)
        logg.debug("%r", req.params)
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    return _tal.processTAL(
        dict(
            creation_date=_get_name_date(
                nodes[0].get("creationtime"), _functools.partial(nodes[0].get, "creator")
               ) if len(nodes)==1 else None,
            err=err,
            fields=mask.metaFields() if hasattr(mask, "i_am_not_a_mask") else None,
            idstr=idstr,
            maskform=mask.getFormHTML(nodes, req) if not hasattr(mask, "i_am_not_a_mask") else None,
            masklist=masks.values(),
            maskname=mask.name,
            node=nodes[0], # ?
            node_count=len(nodes),
            srcnodeid=req.values.get("srcnodeid", ""),
            update_date=_get_name_date(
                nodes[0].updatetime, _functools.partial(nodes[0].get, "updateuser")
               ) if len(nodes)==1 else None,
            user=user,
            language=_core_translation.set_language(req.accept_languages),
            translate=_core_translation.translate,
            csrf=_core_csrfform.get_token(),
        ),
        file="web/edit/modules/metadata.html",
        macro="edit_metadata",
        request=req,
       )
