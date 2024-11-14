# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import flask as _flask
import flask_admin as _flask_admin
import flask_admin.babel as _
import flask_admin.helpers as _
import flask_login as _flask_login
import wtforms as _wtforms
import wtforms.fields as _
import wtforms.validators as _

import core as _core
import core.auth as _
import core.config as _
import core.csrfform as _
import core.database.postgres.user as _
import web as _web
import web.flaskadmin.acl as _
import web.flaskadmin.node as _
import web.flaskadmin.setting as _
import web.flaskadmin.user as _


class _LoginForm(_core.csrfform.CSRFForm):
    """Creates login form for flask-Login."""
    login = _wtforms.fields.StringField(validators=[_wtforms.validators.required()])
    password = _wtforms.fields.PasswordField(validators=[_wtforms.validators.required()])

    def validate_login(self, field):
        user = self.get_user()
        if user is None:
            raise _wtforms.validators.ValidationError('Invalid user')
        if _core.auth.authenticate_user_credentials(self.login.data, self.password.data, _flask.request) is None:
            raise _wtforms.validators.ValidationError('Invalid password')
        _flask.flash('Logged in successfully')

    def get_user(self):
        return _core.db.query(_core.database.postgres.user.User).filter_by(login_name=self.login.data).first()


class _IndexView(_flask_admin.AdminIndexView):
    """Creates index view class for handling login."""
    def __init__(self, name=None, category=None,
                 endpoint=None, url=None,
                 template='admin/index.html',
                 menu_class_name=None,
                 menu_icon_type=None,
                 menu_icon_value=None):
        super(_IndexView, self).__init__(name or _flask_admin.babel.lazy_gettext('Home'),
                                        category,
                                        endpoint or 'admin',
                                        '/f/admin',
                                        'static',
                                        menu_class_name=menu_class_name,
                                        menu_icon_type=menu_icon_type,
                                        menu_icon_value=menu_icon_value)
        self._template = template

    @_flask_admin.expose('/')
    def index(self):
        if not _flask_login.current_user.is_authenticated:
            return _flask.redirect(_flask.url_for('.login_view'))
        return super(_IndexView, self).index()

    @_flask_admin.expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        login_form = _LoginForm(_flask.request.form)

        if _flask_admin.helpers.validate_form_on_submit(login_form):
            user = login_form.get_user()
            _flask_login.login_user(user)
        if _flask_login.current_user.is_authenticated:
            return _flask.redirect(_flask.url_for('.index'))
        self._template_args['form'] = login_form
        return super(_IndexView, self).index()

    @_flask_admin.expose('/logout/')
    def logout_view(self):
        user = _flask_login.current_user
        _core.auth.logout_user(user, _flask.request)
        _flask_login.logout_user()
        return _flask.redirect(_flask.url_for('.index'))


def init_flask_app(app):
    """
    Initializes flask-login.
    Creates the mediaTUM-admin Flask app.
    """
    login_manager = _flask_login.LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return _core.db.query(_core.database.postgres.user.User).get(user_id)

    admin = _flask_admin.Admin(
        app,
        name="mediaTUM",
        template_mode="bootstrap3",
        index_view=_IndexView(),
        base_template='admin_base.html',
        )

    if not _core.config.getboolean("admin.activate", True):
        return

    admin.add_view(_web.flaskadmin.user.UserView())
    admin.add_view(_web.flaskadmin.user.UserGroupView())
    admin.add_view(_web.flaskadmin.user.AuthenticatorInfoView())
    admin.add_view(_web.flaskadmin.user.OAuthUserCredentialsView())

    admin.add_view(_web.flaskadmin.node.NodeView())
    admin.add_view(_web.flaskadmin.node.FileView())

    admin.add_view(_web.flaskadmin.setting.SettingView())

    admin.add_view(_web.flaskadmin.acl.AccessRuleView())
    admin.add_view(_web.flaskadmin.acl.AccessRulesetView())
    admin.add_view(_web.flaskadmin.acl.AccessRulesetToRuleView())
