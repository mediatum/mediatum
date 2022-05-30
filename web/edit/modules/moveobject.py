# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

from contenttypes import Data as _Data
from core import db as _db

_q = _db.query

def getContent(req, ids):
    _node = _q(_Data).get(long(ids[0]))
    return _tal.processTAL(
            dict(nodeid=_node.id, srcnodeid=req.values.get("srcnodeid", ""), action='move'),
            file="web/edit/modules/movecopyobject.html",
            macro="view_node",
            request=req,
        )
