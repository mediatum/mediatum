# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

from contenttypes import Data
from core import db
from utils.utils import getFormatedString

q = db.query

def getContent(req, ids):
    node = q(Data).get(long(ids[0]))

    if hasattr(node, "show_node_big"):
        return _tal.processTAL({'content': getFormatedString(node.show_node_big(req))}, file="web/edit/modules/view.html", macro="view_node", request=req)
    else:
        return _tal.processTAL({}, file="web/edit/modules/view.html", macro="view_noview", request=req)
