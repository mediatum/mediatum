# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

import web as _web
import web.flaskadmin.baseadminview as _
from core import db
from core.database.postgres.setting import Setting

logg = logging.getLogger(__name__)


class SettingView(_web.flaskadmin.baseadminview.BaseAdminView):

    form_columns = ("key", "value")

    can_create = False
    can_edit = False

    def __init__(self, session=db.session, *args, **kwargs):

        super(SettingView, self).__init__(Setting, session, *args, **kwargs)
