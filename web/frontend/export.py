# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import core.httpstatus as _httpstatus
from core import db
from core.translation import t
from contenttypes import Data
from sqlalchemy.orm.exc import NoResultFound
from core.request_handler import error as _error

q = db.query

logg = logging.getLogger(__name__)


def export(req):
    p = req.mediatum_contextfree_path[1:].split("/")

    if len(p) != 2:
        _error(req, 404, "Object not found")
        return

    if p[0].isdigit():
        try:
            node = q(Data).get(p[0])
            if not node:
                return _error(req, 404, "Object not found")
        except:
            return _error(req, 404, "Object not found")
    else:
        return _error(req, 404, "Object not found")

    if not node.has_read_access():
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        req.response.set_data(t(req, "permission_denied"))
        return

    mask = node.metadatatype.getMask(p[1])
    if mask:
        try:
            req.response.status_code = _httpstatus.HTTP_OK
            req.response.set_data(mask.getViewHTML([node], flags=8))
            req.response.content_type = "text/plain; charset=utf-8"
        except NoResultFound:
            return _error(req, 404, "Object not found")
    else:
        _error(req, 404, "Object not found")
        return
