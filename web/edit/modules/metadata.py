# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import functools as _functools
import httplib as _httplib
import logging

import flask as _flask
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from utils.date import format_date, parse_date
from core import db
from core.database.postgres.node import Node
from core.users import user_from_session
import schema.schema as _schema

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


class _SystemMask(_schema.Mask):

    @property
    def all_maskitems(self):
        return self.children

    @property
    def maskitems(self):
        return self.children


class _SystemMaskitem(_schema.Maskitem):

    @property
    def metafield(self):
        return self.children.one()

    def getField(self):
        return self.metafield


def _handle_edit_metadata(req, mask, nodes):
    # check and save items
    user = user_from_session()
    userdir = user.home_dir
    form = req.form

    for node in nodes:
        assert node.has_write_access() and node is not userdir

    attrs = mask.get_edit_update_attrs(req, user)
    if not attrs.errors:
        for node in nodes:
            mask.apply_edit_update_attrs_to_node(node, attrs)

    db.session.commit()
    return attrs.errors


def getContent(req, ids):
    user = user_from_session()

    if "metadata" in user.hidden_edit_functions:
        logg.error("edit function is hidden")
        req.response.status_code = _httplib.FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    err = 0

    nodes = map(q(Node).get, ids)

    if not all(node.has_write_access() for node in nodes):
        req.response.status_code = _httplib.FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    logg.info("%s in editor metadata: %r", user.login_name, [[n.id, n.name, n.type]for n in nodes])

    if len(frozenset(node.schema for node in nodes))!=1:
        logg.info("%s user error: multiple metatypes in editor not supported", user.login_name)
        return _tal.processTAL({}, file="web/edit/modules/metadata.html", macro="multiple_documents_not_supported", request=req)

    idstr = ",".join(ids)

    masks = {}
    if hasattr(nodes[-1], "metaFields") and len(frozenset(node.type for node in nodes)) == 1:
        masks["settings"] = _SystemMask("settings")
        masks["settings"].setMasktype("edit")
        masks["settings"].setDescription(_core_translation.translate_in_request("settings", req))

        for orderpos,metafield in enumerate(nodes[-1].metaFields(_core_translation.set_language(req.accept_languages))):
            maskitem = _SystemMaskitem(metafield.label, orderpos=orderpos)
            maskitem.set('type', 'field')
            masks["settings"].children.append(maskitem)
            maskitem.children.append(metafield)

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
            req.response.status_code = _httplib.FORBIDDEN
            return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

        errors = _handle_edit_metadata(req, mask, nodes)
        errors = {_schema.sanitize_metafield_name(name):error.get_translated_message() for name,error in errors.iteritems()}
        logg.debug("%s change metadata %s", user.login_name, idstr)
        logg.debug("%r", req.params)
        req.response = _flask.jsonify(errors)
        return req.response.status_code

    return _tal.processTAL(
        dict(
            creation_date=_get_name_date(
                nodes[0].get("creationtime"), _functools.partial(nodes[0].get, "creator")
               ) if len(nodes)==1 else None,
            err=err,
            idstr=idstr,
            maskform=mask.getFormHTML(nodes, req),
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
