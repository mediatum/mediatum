# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

from web import admin as _web_admin


def validate(req, op):
    return _tal.processTAL(
        dict(navigation=_web_admin.adminutils.adminNavigation()),
        file="/web/admin/modules/default.html",
        macro="view",
        request=req,
        )
