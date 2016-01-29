# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import logging
from core import db, User, UserGroup, AuthenticatorInfo
from markupsafe import Markup
from wtforms.fields.core import StringField
from web.newadmin.views import BaseAdminView

logg = logging.getLogger(__name__)


def _link_format_node_id_column(node_id):
    # XXX: just for testing, this should link to this instance
    return Markup('<a href="https://mediatum.ub.tum.de/node?id={0}">{0}</a>'.format(node_id))


class UserView(BaseAdminView):

    column_exclude_list = ("created", "password_hash", "salt", "comment", "private_group", "can_edit_shoppingbag", "can_change_password")
    column_filters = ("authenticator_info", "display_name", "login_name", "organisation")
    can_export = True

    column_formatters = {
        "home_dir": lambda v, c, m, p: _link_format_node_id_column(m.home_dir.id) if m.home_dir else None
    }
    column_searchable_list = ("display_name", "login_name", "organisation")
    column_editable_list = ("login_name", "email")
    form_excluded_columns = ("home_dir", "created", "password_hash", "salt", "versions", "shoppingbags", "private_group")

    form_overrides = {
        "email": StringField
    }

    def __init__(self, session=db.session, *args, **kwargs):
        super(UserView, self).__init__(User, session, category="User", *args, **kwargs)


class UserGroupView(BaseAdminView):

    def __init__(self, session=db.session, *args, **kwargs):
        super(UserGroupView, self).__init__(UserGroup, session, category="User", *args, **kwargs)


class AuthenticatorInfoView(BaseAdminView):

    def __init__(self, session=db.session, *args, **kwargs):
        super(AuthenticatorInfoView, self).__init__(AuthenticatorInfo, session, category="User", *args, **kwargs)
