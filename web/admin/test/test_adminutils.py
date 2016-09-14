# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.transition import current_user
from pytest import raises
from web.admin.adminutils import become_user
from core.exceptions import SecurityException


def test_become_user(session, req, admin_user, some_user):
    session.flush()
    req.session["user_id"] = admin_user.id
    user = become_user(some_user.login_name)
    assert user is some_user
    assert current_user == some_user


def test_become_user_not_allowed_for_guest(session, req, guest_user, some_user):
    session.flush()
    req.session["user_id"] = some_user.id
    with raises(SecurityException):
        become_user(some_user.login_name)


def test_become_user_not_allowed_for_non_admin_user(req, some_user, guest_user):
    with raises(SecurityException):
        become_user(guest_user.login_name)
