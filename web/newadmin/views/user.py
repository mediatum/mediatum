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
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms import SelectMultipleField
from flask.ext.admin import form
from core.auth import INTERNAL_AUTHENTICATOR_KEY
from core.permission import get_or_add_access_rule
from core.database.postgres.permission import AccessRuleset, AccessRulesetToRule, NodeToAccessRuleset
from schema.schema import Metadatatype

q = db.query
logg = logging.getLogger(__name__)


def _link_format_node_id_column(node_id):
    # XXX: just for testing, this should link to this instance
    return Markup('<a href="https://mediatum.ub.tum.de/node?id={0}">{0}</a>'.format(node_id))

class UserView(BaseAdminView):

    column_exclude_list = ("created", "password_hash", "salt", "comment",
                           "private_group", "can_edit_shoppingbag", "can_change_password")
    column_filters = ("authenticator_info", "display_name", "login_name", "organisation")
    can_export = True

    column_details_list = ("home_dir", "authenticator_info", "id", "login_name", "display_name", "lastname",
                           "firstname", "telephone", "organisation", "comment", "email", "password_hash",
                           "salt", "last_login", "active", "can_edit_shoppingbag", "can_change_password",
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
                             "versions", "shoppingbags", "private_group", "group_assocs")

    form_overrides = {
        "email": StringField
    }

    form_extra_fields = {
        "groups": QuerySelectMultipleField(query_factory=lambda: db.query(UserGroup).order_by(UserGroup.name),
                                           widget=form.Select2Widget(multiple=True)),
        "password": StringField()
    }

    def __init__(self, session=None, *args, **kwargs):
        super(UserView, self).__init__(User, session, category="User", *args, **kwargs)

    def on_model_change(self, form, user, is_created):
        if form.password.data and user.authenticator_info.authenticator_key == INTERNAL_AUTHENTICATOR_KEY:
            user.change_password(form.password.data)

class UserGroupView(BaseAdminView):

    form_excluded_columns = "user_assocs"
    column_details_list = ["id", "name", "description", "hidden_edit_functions", "is_editor_group",
                           "is_workflow_editor_group", "is_admin_group", "created_at", "metadatatype_access", "user_names"]

    column_searchable_list = ("name", "description")

    column_filters = ("name", "description", "is_editor_group", "is_workflow_editor_group", "is_admin_group")
    can_export = True

    column_labels = dict(metadatatype_access = 'Metadatatypes', user_names = 'Users')

    edit_functions = ['acls', 'admin', 'changeschema', 'classes', 'editor', 'files', 'ftp', 'identifier',
                      'license', 'logo', 'lza',
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

    def on_form_prefill(self, form, id):
        form.metadatatypes.data = form._obj.metadatatype_access

    def on_model_change(self, form, usergroup, is_created):
        if is_created:
            """ create ruleset for group """
            existing_ruleset = q(AccessRuleset).filter_by(name=usergroup.name).scalar()
            if existing_ruleset is None:
                rule = get_or_add_access_rule(group_ids=[usergroup.id])
                ruleset = AccessRuleset(name=usergroup.name, description=usergroup.name)
                arr = AccessRulesetToRule(rule=rule)
                ruleset.rule_assocs.append(arr)

        """ add/remove access to Metadatatypes """
        for mt in q(Metadatatype):
            nrs_list = q(NodeToAccessRuleset).filter_by(nid=mt.id).filter_by(ruleset_name=usergroup.name).all()
            if mt in form.metadatatypes.data:
                if not nrs_list:
                    mt.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=usergroup.name, ruletype=u'read'))
            else:
                for nrs in nrs_list:
                    mt.access_ruleset_assocs.remove(nrs)



    def __init__(self, session=None, *args, **kwargs):
        super(UserGroupView, self).__init__(UserGroup, session, category="User", *args, **kwargs)


class AuthenticatorInfoView(BaseAdminView):

    def __init__(self, session=None, *args, **kwargs):
        super(AuthenticatorInfoView, self).__init__(AuthenticatorInfo, session, category="User", *args, **kwargs)
