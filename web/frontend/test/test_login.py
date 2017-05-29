# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture

from web.frontend import login
from core.auth import PasswordsDoNotMatch, WrongPassword, PasswordChangeNotAllowed
from core import app


@fixture(autouse=True)
def login_patch(monkeypatch, user, nav_frame):
    import core.users
    import web.frontend.frame
    monkeypatch.setattr(core.users, "user_from_session", lambda req: user)
    monkeypatch.setattr(user, "is_anonymous", False, raising=False)
    monkeypatch.setattr(web.frontend.frame, "render_page", lambda req, node, content_html: "")
    pass

LOGIN_NAME = "username"
PASSWORD = "password"
NEW_PASSWORD = "newsecurepass"
NEW_PASSWORD_REPEATED = "wrongpass"


@fixture
def check_auth_call(user, req):
    """Checks if the login view passes the right parameters and returns a fake user"""
    def _check(login_name, password, _req):
        assert login_name == LOGIN_NAME
        assert password == PASSWORD
        assert req == _req
        return user

    return _check


@fixture
def auth_success_patch(collections, monkeypatch, check_auth_call, session):
    import core.auth
    from core import db
    db.session.add(collections)
    monkeypatch.setattr(core.auth, "authenticate_user_credentials", check_auth_call)


def check_pwdchange(user, req, exception):
    def _check(_user, old_password, new_password, new_password_repeated, _req):
        assert old_password == PASSWORD
        assert new_password == NEW_PASSWORD
        assert new_password_repeated == NEW_PASSWORD_REPEATED
        assert user == _user
        assert req == _req

        if exception is not None:
            raise exception

    return _check


@fixture(params=[None, WrongPassword, PasswordsDoNotMatch, PasswordChangeNotAllowed])
def pwdchange_patch(monkeypatch, request, req, guest_user, user):
    exception = request.param
    import core.auth
    monkeypatch.setattr(core.auth, "change_user_password", check_pwdchange(user, req, exception))
    if exception is None:
        return 302
    return 200


@fixture
def logout_patch(monkeypatch, user):
    import core.auth
    _user = user

    def check_logout_call(user, req):
        assert user == _user
        return True

    monkeypatch.setattr(core.auth, "logout_user", check_logout_call)


def test_login(auth_success_patch, req):
    req.form["LoginSubmit"] = True
    req.form["user"] = LOGIN_NAME
    req.form["password"] = PASSWORD
    assert login.login(req) == 302

def test_logout(logout_patch, req):
    assert login.logout(req) == 302
    assert "user" not in req.session


def test_pwdchange(pwdchange_patch, req, session, collections):
    from core.webconfig import init_theme, add_template_globals
    from core import webconfig
    init_theme()
    webconfig.theme.make_jinja_loader()
    add_template_globals()
    req.form["ChangeSubmit"] = True
    req.form["user"] = LOGIN_NAME
    req.form["password_old"] = PASSWORD
    req.form["password_new1"] = NEW_PASSWORD
    req.form["password_new2"] = NEW_PASSWORD_REPEATED
    with app.test_request_context():
        assert login.pwdchange(req) == pwdchange_patch


# Referer tests

def test_login_no_referer(req):
    from core.webconfig import init_theme, add_template_globals
    from core import webconfig
    init_theme()
    webconfig.theme.make_jinja_loader()
    with app.test_request_context():
        assert login.login(req) == 200
        assert req.session["return_after_login"] is False


def test_login_from_login_page(req):
    from core.webconfig import init_theme, add_template_globals
    from core import webconfig
    init_theme()
    webconfig.theme.make_jinja_loader()
    req.headers["Referer"] = "/login"
    with app.test_request_context():
        assert login.login(req) == 200
        assert req.session["return_after_login"] is False


def test_login_login_from_edit(req):
    from core.webconfig import init_theme, add_template_globals
    from core import webconfig
    init_theme()
    webconfig.theme.make_jinja_loader()
    req.headers["Referer"] = "http://localhost/edit/edit_content?id=604993"
    req.headers["Host"] = "localhost"
    with app.test_request_context():
        assert login.login(req) == 200
        assert req.session["return_after_login"] == "http://localhost/edit?id=604993"


def test_login_from_other(req):
    from core.webconfig import init_theme, add_template_globals
    from core import webconfig
    init_theme()
    webconfig.theme.make_jinja_loader()
    ref = "http://localhost/justatest"
    req.headers["Host"] = "localhost"
    req.headers["Referer"] = ref
    with app.test_request_context():
        assert login.login(req) == 200
        assert req.session["return_after_login"] == ref


def test_new_nodecache():
    """ create a new memory_nodecache for later tests like test_search.py """
    from core.nodecache import new_nodecache
    new_nodecache()
