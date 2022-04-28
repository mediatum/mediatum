# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal
import web.edit.edit_common as _web_edit_edit_common

def getContent(req, ids):
    show_dir_nav = _web_edit_edit_common.ShowDirNav(req)
    return _tal.processTAL(
            dict(nodeids=show_dir_nav.get_ids_from_req(), action='copy'),
            file="web/edit/modules/movecopyall.html",
            macro="view_node",
            request=req,
        )
