# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from core import db
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user


class BaseAdminView(ModelView):

    """Basic settings for all our admin views. All views should inherit this.
    """

    column_display_pk = True
    can_view_details = True

    def __init__(self, model, session=None, *args, **kwargs):
        super(BaseAdminView, self).__init__(model, session or db.Session, *args, **kwargs)

    def is_accessible(self):
        # view access only allowed for admins!
        return current_user.is_authenticated and current_user.is_admin
