# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture

from web.frontend import login


@fixture(autouse=True)
def login_patch(monkeypatch, user, nav_frame):
    import core.users
    import web.frontend.frame
    monkeypatch.setattr(core.users, "user_from_session", lambda req: user)
    monkeypatch.setattr(web.frontend.frame, "getNavigationFrame", lambda req: nav_frame)

LOGIN_NAME = "username"
PASSWORD = "password"


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
def auth_success_patch(collections, monkeypatch, check_auth_call):
    import core.auth
    from core import db
    db.session.add(collections)
    monkeypatch.setattr(core.auth, "authenticate_user_credentials", check_auth_call)
    
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


def test_login_change_to_browsing(req):
    req.form["arg1"] = "val1"
    req.form["arg2"] = "val2"
    req.form["arg3"] = "val3"
    assert login.login(req) == 302
    assert req.request.mock_


# Referer tests

def test_login_no_referer(req):
    assert login.login(req) == 200
    assert req.session["return_after_login"] is False


def test_login_from_login_page(req):
    req.header.append("Referer: /login")
    assert login.login(req) == 200
    assert req.session["return_after_login"] is False


def test_login_login_from_edit(req):
    req.header.append("Referer: /edit/edit_content?id=604993")
    assert login.login(req) == 200
    assert req.session["return_after_login"] == "/edit"


def test_login_from_other(req):
    ref = "http://localhost:8081/justatest"
    req.header.append("Referer: " + ref)
    assert login.login(req) == 200
    assert req.session["return_after_login"] == ref
