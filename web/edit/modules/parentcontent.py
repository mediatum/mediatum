# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re as _re
import mediatumtal.tal as _tal

from contenttypes import Data
from core import db
from utils.utils import getFormatedString

q = db.query

def getContent(req, ids):
    node = q(Data).get(long(ids[0]))
    parent = node.parents[0]
    sortfield = 'off'
    if not sortfield:
        sortfield = "off"

    nodesperpage = '20'

    return _tal.processTAL({'id': parent.id, 'sortfield': sortfield, 'nodesperpage': nodesperpage},file="web/edit/modules/nodesperpage.html", macro="view_node", request=req)
