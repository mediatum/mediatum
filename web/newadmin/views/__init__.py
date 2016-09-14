# -*- coding: utf-8 -*-
"""
    web.newadmin.views
    ~~~~~~~~~~~~~~~~~~
    this package is part of mediatum - a multimedia content repository

    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core import db
from flask_admin.contrib.sqla import ModelView
from flask.ext import login


class BaseAdminView(ModelView):

    """Basic settings for all our admin views. All views should inherit this.
    """

    column_display_pk = True
    can_view_details = True

    def __init__(self, model, session=None, *args, **kwargs):
        super(BaseAdminView, self).__init__(model, session or db.Session, *args, **kwargs)

    def is_accessible(self):
        # view access only allowed for admins!
        return login.current_user.is_authenticated and login.current_user.is_admin
