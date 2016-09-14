# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from web.handlers.become import become_user
from core.transition import httpstatus


def test_become(session, req, admin_user, some_user):
    session.flush()
    req.session["user_id"] = admin_user.id
    req.path = "/_become/" + some_user.login_name
    status = become_user(req)
    assert status == httpstatus.HTTP_MOVED_TEMPORARILY
    assert req["Location"] == "/"


def test_become_with_authenticator(session, req, admin_user, some_user):
    session.flush()
    user = some_user
    req.session["user_id"] = admin_user.id
    req.path = "/_become/{}|{}/{}".format(user.authenticator_info.auth_type,
                                          user.authenticator_info.name,
                                          user.login_name)
    status = become_user(req)
    assert status == httpstatus.HTTP_MOVED_TEMPORARILY
    assert req["Location"] == "/"


def test_become_guest_not_allowed(req, guest_user):
    req.path = "/_become/admin"
    error = become_user(req)
    assert error == 404


def test_become_guest_invalid_url(req, guest_user):
    req.path = "/_become/a/b/c"
    error = become_user(req)
    assert error == 404

