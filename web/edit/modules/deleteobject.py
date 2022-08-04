# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import core as _core
from contenttypes import Data
from mediatumtal import tal as _tal


def getContent(req, ids):
    node = _core.db.query(Data).get(long(ids[0]))
    return _tal.processTAL(
            dict(srcnodeid=req.values.get("srcnodeid", ""), id=node.id),
            file="web/edit/modules/deleteobject.html",
            macro="view_node",
            request=req,
        )
