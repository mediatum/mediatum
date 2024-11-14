# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import flask as _flask
import flask_login as _flask_login
from flask_admin import Admin
from web.admin.views.user import UserView, UserGroupView, AuthenticatorInfoView, OAuthUserCredentialsView
from wtforms import fields, validators

import core as _core
from core import db
from core import config
from core.database.postgres.user import User
from core.auth import authenticate_user_credentials, logout_user
from flask_admin import AdminIndexView
from flask_admin import helpers, expose
from flask_admin.babel import lazy_gettext as _lazy_gettext
from web.admin.views.node import NodeView, FileView
from web.admin.views.setting import SettingView
from web.admin.views.acl import AccessRulesetView, AccessRuleView, AccessRulesetToRuleView
import core.csrfform as _core_csrfform
from core.request_handler import handle_request as _handle_request

q = db.query


class IndexView(AdminIndexView):
    """Creates index view class for handling login."""
    def __init__(self, name=None, category=None,
                 endpoint=None, url=None,
                 template='admin/index.html',
                 menu_class_name=None,
                 menu_icon_type=None,
                 menu_icon_value=None):
        super(IndexView, self).__init__(name or _lazy_gettext('Home'),
                                        category,
                                        endpoint or 'admin',
                                        '/f/admin',
                                        'static',
                                        menu_class_name=menu_class_name,
                                        menu_icon_type=menu_icon_type,
                                        menu_icon_value=menu_icon_value)
        self._template = template

    @expose('/')
    def index(self):
        if not _flask_login.current_user.is_authenticated:
            return _flask.redirect(_flask.url_for('.login_view'))
        return super(IndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        login_form = LoginForm(_flask.request.form)

        if helpers.validate_form_on_submit(login_form):
            user = login_form.get_user()
            _flask_login.login_user(user)
        if _flask_login.current_user.is_authenticated:
            return _flask.redirect(_flask.url_for('.index'))
        self._template_args['form'] = login_form
        return super(IndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        user = _flask_login.current_user
        logout_user(user, _flask.request)
        _flask_login.logout_user()
        return _flask.redirect(_flask.url_for('.index'))


class LoginForm(_core_csrfform.CSRFForm):
    """Creates login form for flask-Login."""
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()
        if user is None:
            raise validators.ValidationError('Invalid user')
        if authenticate_user_credentials(self.login.data, self.password.data, _flask.request) is None:
            raise validators.ValidationError('Invalid password')
        _flask.flash('Logged in successfully')

    def get_user(self):
        return q(User).filter_by(login_name=self.login.data).first()


def make_admin_app(app):
    """Creates the mediaTUM-admin Flask app.
    """
    admin = Admin(
        app,
        name="mediaTUM",
        template_mode="bootstrap3",
        index_view=IndexView(),
        base_template='admin_base.html',
        )

    admin_enabled = config.getboolean("admin.activate", True)
    if admin_enabled:
        admin.add_view(UserView())
        admin.add_view(UserGroupView())
        admin.add_view(AuthenticatorInfoView())
        admin.add_view(OAuthUserCredentialsView())

        admin.add_view(NodeView())
        admin.add_view(FileView())

        admin.add_view(SettingView())

        admin.add_view(AccessRuleView())
        admin.add_view(AccessRulesetView())
        admin.add_view(AccessRulesetToRuleView())

    return admin


def flask_routes(app):
    @app.route('/')
    @app.route('/login', methods=['GET', 'POST'])
    @app.route('/logout')
    @app.route('/edit')
    @app.route('/admin/')
    @app.route('/publish/')
    @app.route('/pwdchange', methods=['GET', 'POST'])
    @app.route('/pwdforgotten')
    @app.route('/mask', methods=['GET', 'POST'])
    @app.route('/node', methods=['GET', 'POST'])
    @app.route('/edit/<path:action>', methods=['GET', 'POST'])
    @app.route('/admin/<path:action>', methods=['GET', 'POST'])
    @app.route('/services/<path:action>')
    @app.route('/ftree/<path:action>', methods=['GET', 'POST'])
    @app.route('/publish/<path:action>')
    @app.route('/thumbnail/<path:action>')
    @app.route('/image/<path:action>')
    @app.route('/doc/<path:action>')
    @app.route('/file/<path:action>')
    @app.route('/download/<path:action>')
    @app.route('/<path:action>')
    def action(action=None):
        req = _handle_request(_flask.request)
        return req.response


def init_login(app):
    """Initializes flask-login."""
    login_manager = _flask_login.LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return q(User).get(user_id)


make_admin_app(_core.app)
init_login(_core.app)
flask_routes(_core.app)
