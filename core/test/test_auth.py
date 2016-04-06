# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises, fixture, yield_fixture
from mock import MagicMock
import core.auth
from core.auth import PasswordsDoNotMatch, change_user_password, PasswordChangeNotAllowed, Authenticator, create_password_hash,\
    check_user_password
from munch import Munch


FAKE_AUTHENTICATOR_KEY = (u"fake", u"fakename")

TEST_PASSWORD = u"täst"
TEST_SALT = "salt"
TEST_HASH = "/j2XlL3HyHsJrQ6PDyzYqY+Xqd3XnULSSIzd7N2hPNpWS8pXPH9mlkHhl4fzQtSMSKJifjdayh8MJ0Ltv+irJQ=="

class FakeAuthenticator(Authenticator):
    auth_type = FAKE_AUTHENTICATOR_KEY[0]


@fixture
def fake_authenticator():
    authenticator = FakeAuthenticator(FAKE_AUTHENTICATOR_KEY[1])
    return authenticator


@fixture
def auth_order(monkeypatch):
    auth_order = [(u"internal", u"default"), (u"fake", u"fakename")]
    order_str = u",".join(u"{}|{}".format(*a) for a in auth_order)
    monkeypatch.setattr("core.auth.config", {u"auth.authenticator_order": order_str})
    return auth_order


def test_create_password_hash():
    hashed_pw, salt = create_password_hash(TEST_PASSWORD, TEST_SALT)
    assert salt == TEST_SALT
    assert hashed_pw == TEST_HASH


def test_check_user_password():
    user = Munch(salt=TEST_SALT, password_hash=TEST_HASH)
    pass_ok = check_user_password(user, TEST_PASSWORD)
    assert pass_ok


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


def test_auth_init_no_config():
    """No config, so only the default internal authenticator should be present"""
    core.auth.init()
    assert len(core.auth.authenticators) == 1
    assert core.auth.authenticators.keys()[0] == core.auth.INTERNAL_AUTHENTICATOR_KEY


def test_register_authenticator_no_config(fake_authenticator):
    """No config, so only the default internal authenticator should be present even if we register an authenticator."""
    from core.auth import register_authenticator
    core.auth.init()
    register_authenticator(fake_authenticator)
    assert len(core.auth.authenticators) == 1
    assert core.auth.authenticators.keys()[0] == core.auth.INTERNAL_AUTHENTICATOR_KEY


def test_register_authenticator(fake_authenticator, auth_order):
    """No config, so only the default internal authenticator should be present even if we register an authenticator."""
    from core.auth import register_authenticator
    core.auth.init()
    register_authenticator(fake_authenticator)
    assert len(core.auth.authenticators) == 2
    assert core.auth.authenticators.keys()[0] == core.auth.INTERNAL_AUTHENTICATOR_KEY
    assert core.auth.authenticators.keys()[1] == FAKE_AUTHENTICATOR_KEY


def test_get_configured_authenticator_order(auth_order):
    import core.auth
    normal_conf = core.auth.config
    actual_auth_order = core.auth.get_configured_authenticator_order()
    assert actual_auth_order == auth_order
    core.auth.config = normal_conf

