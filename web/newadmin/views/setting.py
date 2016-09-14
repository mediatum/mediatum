# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import logging
from core import db, Setting
from web.newadmin.views import BaseAdminView

logg = logging.getLogger(__name__)


class SettingView(BaseAdminView):

    form_columns = ("key", "value")

    can_create = False
    can_edit = False

    def __init__(self, session=db.session, *args, **kwargs):

        super(SettingView, self).__init__(Setting, session, *args, **kwargs)
