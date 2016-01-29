# -*- coding: utf-8 -*-
"""
    web.newadmin
    ~~~~~~~~~~~~

    This is the new admin interface for mediaTUM.
    It is implemented as a Flask app using flask-admin.

    this package is part of mediatum - a multimedia content repository
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from flask import Flask
from flask_admin import Admin
from web.newadmin.views.user import UserView, UserGroupView, AuthenticatorInfoView


def make_app():
    """Creates the mediaTUM-admin Flask app.
    When more parts of mediaTUM are converted to Flask, we might use a "global" app to which the admin interface is added.
    """
    admin_app = Flask("mediaTUM admin")
    admin_app.debug = True
    admin_app.config["SECRET_KEY"] = "dev"
    admin = Admin(admin_app, name="mediaTUM", template_mode="bootstrap3")

    admin.add_view(UserView())
    admin.add_view(UserGroupView())
    admin.add_view(AuthenticatorInfoView())

    return admin_app


app = make_app()
