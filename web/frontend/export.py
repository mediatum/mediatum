# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import httplib as _httplib
import logging

import core.translation as _core_translation
from core import db
from contenttypes import Data
from sqlalchemy.orm.exc import NoResultFound

q = db.query

logg = logging.getLogger(__name__)


def export(req):
    p = req.mediatum_contextfree_path[1:].split("/")
    if len(p) != 2 or not p[0].isdigit():
        req.response.set_data("Object not found")
        req.response.status_code = _httplib.NOT_FOUND
        return

    try:
        node = q(Data).get(p[0])
    except:
        req.response.set_data("Object not found")
        req.response.status_code = _httplib.NOT_FOUND
        return

    if not node:
        req.response.set_data("Object not found")
        req.response.status_code = _httplib.NOT_FOUND
        return

    if not node.has_read_access():
        req.response.status_code = _httplib.FORBIDDEN
        req.response.set_data(_core_translation.translate_in_request("permission_denied", req))
        return

    mask = node.metadatatype.getMask(p[1])
    if not mask:
        req.response.set_data("Object not found")
        req.response.status_code = _httplib.NOT_FOUND
        return

    try:
        req.response.status_code = _httplib.OK
        req.response.set_data(mask.getViewHTML([node], flags=8))
        req.response.content_type = "text/plain; charset=utf-8"
    except NoResultFound:
        req.response.set_data("Object not found")
        req.response.status_code = _httplib.NOT_FOUND
