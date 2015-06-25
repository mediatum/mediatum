# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises
from mock import MagicMock
from core.auth import PasswordsDoNotMatch, change_user_password, PasswordChangeNotAllowed


def test_change_user_password_do_not_match(some_user):
    req = MagicMock()
    some_user.can_change_password = True
    with raises(PasswordsDoNotMatch):
        change_user_password(some_user, u"test", u"changedpw", u"changedpwWRONG", req)


def test_change_user_password_not_allowed(some_user):
    req = MagicMock()
    some_user.can_change_password = False
    with raises(PasswordChangeNotAllowed):
        change_user_password(some_user, u"test", u"gedened", u"gedened", req)
