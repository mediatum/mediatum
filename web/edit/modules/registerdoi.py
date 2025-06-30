# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import urlparse as _urlparse
from requests import exceptions as _requests_exceptions

import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
from core import config as _core_config
from core import db
from core import translation as _core_translation
from core import users as _core_users
from core.database.postgres import node as _postgres_node
from export import doi as _export_doi

logg = _logging.getLogger(__name__)
q = db.query


def getContent(req, ids):
    id_, = ids
    user = _core_users.user_from_session()
    if not user.is_admin:
        raise RuntimeError("Permission denied for user: {}".format(user.id))

    if req.values.get("back"):
        return _tal.processTAL(
            dict(id=id_, srcnodeid=req.values.get("srcnodeid", "")),
            file="web/edit/modules/registerdoi.html",
            macro="view_node",
            request=req,
            )

    node = q(_postgres_node.Node).get(id_)

    tal_context = dict(
        csrf=_core_csrfform.get_token(),
        event=None if req.values.get("event", "none") == "none" else req.values["event"],
        id=id_,
        nodename=node.getName(),
        masks=node.metadatatype.getMasks(),
        srcnodeid=req.values.get("srcnodeid", ""),
        prefix=_core_config.settings["doi-registration.prefix"],
        suffix=req.values.get("suffix"),
        translate=_core_translation.translate_in_template,
        url=req.values.get("url", _urlparse.urljoin(req.host_url, str(id_))),
        )
    if req.method == "POST":
        if not req.values.get("mask"):
            raise RuntimeError("missing metadata mask")
        if not req.values["mask"].startswith("1.") and req.values["mask"] != "0":
            raise RuntimeError(u"unvalid metadata mask {}".format(req.values["mask"]))
        tal_context["selected_mask"] = req.values["mask"][2:] if req.values["mask"].startswith("1.") else None
        try:
            _export_doi.registerdoi(
                node,
                tal_context["selected_mask"],
                req.values["url"],
                req.values["suffix"],
                tal_context["event"],
                req.values.get("create") or req.values.get("update") or req.values.get("update-create"),
                )
        except _requests_exceptions.HTTPError:
            logg.exception("editor doi registration failed")
            tal_context["status"] = False
        else:
            tal_context["status"] = True
    else:
        tal_context["status"] = None
        tal_context["selected_mask"] = node.metadatatype.get_mask("doi") and "doi"

    return _tal.processTAL(tal_context, file="web/edit/modules/registerdoi.html", macro="registerdoi", request=req)
