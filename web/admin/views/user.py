# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools as _functools
import logging

import core as _core
import core.database.postgres.permission as _
from core import db
from core.database.postgres.user import AuthenticatorInfo
from core.database.postgres.user import User
from core.database.postgres.user import UserGroup
from markupsafe import Markup
from wtforms.fields.core import StringField
from web.admin.views import BaseAdminView
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms import SelectMultipleField
from flask_admin import form, expose

import core.csrfform as _core_csrfform
from core.auth import INTERNAL_AUTHENTICATOR_KEY
from core.permission import get_or_add_access_rule
from schema.schema import Metadatatype
from core.database.postgres.user import OAuthUserCredentials

q = db.query
logg = logging.getLogger(__name__)


def _link_format_node_id_column(node_id):
    # XXX: just for testing, this should link to this instance
    return Markup('<a href="/node?id={0}" class="mediatum-link-mediatum">{0}</a>'.format(node_id))


def _update_access_ruleset_assocs(ruleset_name, add_metadatatypes, drop_metadatatypes):
    """
    add/remove access to Metadatatypes
    """
    mkquery = _functools.partial(
        q(_core.database.postgres.permission.NodeToAccessRuleset).filter_by,
        ruleset_name=ruleset_name,
        )
    nodetoaccessruleset = _core.database.postgres.permission.NodeToAccessRuleset(
        ruleset_name=ruleset_name,
        ruletype=u'read',
        )
    for metadatatype in add_metadatatypes:
        if mkquery(nid=metadatatype.id).scalar() is None:
            metadatatype.access_ruleset_assocs.append(nodetoaccessruleset)
    for metadatatype in drop_metadatatypes:
        if metadatatype not in add_metadatatypes:
            map(metadatatype.access_ruleset_assocs.remove, mkquery(nid=metadatatype.id).all())


class UserView(BaseAdminView):

    can_delete = False

    form_base_class = _core_csrfform.CSRFForm

    column_exclude_list = ("created", "password_hash", "salt", "comment",
                           "private_group", "can_change_password")
    column_filters = ("authenticator_info", "display_name", "login_name", "organisation", "active")
    can_export = True

    column_details_list = ("home_dir", "authenticator_info", "id", "login_name", "display_name", "lastname",
                           "firstname", "telephone", "organisation", "comment", "email", "password_hash",
                           "salt", "last_login", "active", "can_change_password",
                           "created_at", "group_names")
    """
    """

    column_labels = dict(group_names = 'Groups')

    column_formatters = {
        "home_dir": lambda v, c, m, p: _link_format_node_id_column(m.home_dir.id) if m.home_dir else None
    }
    column_searchable_list = ("display_name", "login_name", "organisation")
    column_editable_list = ("login_name", "email")
    form_excluded_columns = ("home_dir", "created", "password_hash", "salt",
                             "versions", "private_group", "group_assocs")

    form_overrides = {
        "email": StringField
    }

    form_extra_fields = {
        "groups": QuerySelectMultipleField(query_factory=lambda: db.query(UserGroup).order_by(UserGroup.name),
                                           widget=form.Select2Widget(multiple=True)),
        "password": StringField(),

    }

    def __init__(self, session=None, *args, **kwargs):
        super(UserView, self).__init__(User, session, category="User", *args, **kwargs)

    def on_model_change(self, form, user, is_created):

        if form.password.data and user.authenticator_info.authenticator_key == INTERNAL_AUTHENTICATOR_KEY:
            user.change_password(form.password.data)

class UserGroupView(BaseAdminView):
    form_base_class = _core_csrfform.CSRFForm

    form_excluded_columns = ("user_assocs", "versions")

    column_details_list = ["id", "name", "description", "hidden_edit_functions", "is_editor_group",
                           "is_workflow_editor_group", "is_admin_group", "created_at", "metadatatype_access", "user_names"]

    column_searchable_list = ("name", "description")

    column_filters = ("name", "description", "is_editor_group", "is_workflow_editor_group", "is_admin_group")
    can_export = True

    column_labels = dict(metadatatype_access = 'Metadatatypes', user_names = 'Users')

    edit_functions = ['acls', 'admin', 'changeschema', 'classes', 'editor', 'files', 'identifier',
                      'logo',
                      'metadata', 'search', 'searchmask', 'sortfiles', 'statsaccess', 'statsfiles', 'upload']

    edit_function_choices = [(x, x) for x in edit_functions]

    form_extra_fields = {
        "users": QuerySelectMultipleField(query_factory=lambda: db.query(User).order_by(User.login_name),
                                          widget=form.Select2Widget(multiple=True)),
        "metadatatypes": QuerySelectMultipleField(query_factory=lambda: db.query(Metadatatype).order_by(Metadatatype.name),
                                          widget=form.Select2Widget(multiple=True)),
        "hidden_edit_functions": SelectMultipleField(choices=edit_function_choices,
                                          widget=form.Select2Widget(multiple=True)),
    }

    def get_edit_form(self):
        form = super(UserGroupView, self).get_edit_form()
        del form.name
        return form

    def on_form_prefill(self, form, id):
        form.metadatatypes.data = q(UserGroup).filter_by(id=id).scalar().metadatatype_access

    def on_model_change(self, form, model, is_created):
        if is_created:
            """ create ruleset for group """
            existing_ruleset = q(_core.database.postgres.permission.AccessRuleset).filter_by(name=model.name).scalar()
            if existing_ruleset is None:
                rule = get_or_add_access_rule(group_ids=(model.id, ))
                ruleset = _core.database.postgres.permission.AccessRuleset(name=model.name, description=model.name)
                arr = _core.database.postgres.permission.AccessRulesetToRule(rule=rule)
                ruleset.rule_assocs.append(arr)
            _update_access_ruleset_assocs(model.name, form.metadatatypes.data, ())
        else:
            _update_access_ruleset_assocs(model.name, form.metadatatypes.data, model.metadatatype_access)

    def __init__(self, session=None, *args, **kwargs):
        super(UserGroupView, self).__init__(UserGroup, session, category="User", *args, **kwargs)


class AuthenticatorInfoView(BaseAdminView):
    form_base_class = _core_csrfform.CSRFForm

    def __init__(self, session=None, *args, **kwargs):
        super(AuthenticatorInfoView, self).__init__(AuthenticatorInfo, session, category="User", *args, **kwargs)


class OAuthUserCredentialsView(BaseAdminView):
    form_base_class = _core_csrfform.CSRFForm
    form_columns = ("user", "oauth_user", "oauth_key")

    def __init__(self, session=None, *args, **kwargs):
        super(OAuthUserCredentialsView, self).__init__(OAuthUserCredentials, session, category="User", *args, **kwargs)
