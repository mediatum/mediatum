# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

def getContent(req, ids):
    return _tal.processTAL({'src': req.params.get("id")}, file="web/edit/modules/editall.html", macro="view_node", request=req)
