# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import hashlib
from pytest import raises
from mock import MagicMock
from core import db
from core.auth import WrongPassword, INTERNAL_AUTHENTICATOR_KEY, create_password_hash, create_md5_hash
from core.database.postgres.user import AuthenticatorInfo


def test_default_internal_auth_in_default_data(default_data):
    q = db.session.query
    auth_type, auth_name = INTERNAL_AUTHENTICATOR_KEY
    auth_info = q(AuthenticatorInfo).one()
    assert auth_info.name == auth_name
    assert auth_info.auth_type == auth_type


def test_authenticate_user_credentials(internal_authenticator, internal_user):
    req = MagicMock()
    should_be_user = internal_authenticator.authenticate_user_credentials(u"testuser", u"test", req)
    assert should_be_user == internal_user


def test_authenticate_user_credentials_rehash_plain_md5(internal_authenticator, internal_user):
    md5_hash = hashlib.md5("insecure").hexdigest()
    internal_user.password_hash = md5_hash
    internal_user.salt = None
    req = MagicMock()
    should_be_user = internal_authenticator.authenticate_user_credentials(u"testuser", u"insecure", req)
    assert should_be_user == internal_user
    # salt must be present now
    assert should_be_user.salt is not None
    # hash must have changed (our secure hashes are longer than md5 ;)
    assert should_be_user.password_hash != md5_hash
    # try again with rehashed password, should return the same user
    should_be_user_rehashed = internal_authenticator.authenticate_user_credentials(u"testuser", u"insecure", req)
    assert should_be_user_rehashed == internal_user


def test_authenticate_user_credentials_rehash_hashed_md5(internal_authenticator, internal_user):
    req = MagicMock()
    md5_hash = create_md5_hash(u"ünsecure")
    password_hash, salt = create_password_hash(md5_hash)
    internal_user.password_hash, internal_user.salt = password_hash, salt
    should_be_user = internal_authenticator.authenticate_user_credentials(u"testuser", u"ünsecure", req)
    assert should_be_user == internal_user
    # salt should change (with rare collisions)
    assert should_be_user.salt != salt
    # hash must change (same hash type, but collisions should be rare ;)
    assert should_be_user.password_hash != password_hash
    # try again with rehashed password, should return the same user
    should_be_user_rehashed = internal_authenticator.authenticate_user_credentials(u"testuser", u"ünsecure", req)
    assert should_be_user_rehashed == internal_user


def test_authenticate_user_credentials_wrong_pass(internal_authenticator, internal_user):
    req = MagicMock()
    should_be_no_user = internal_authenticator.authenticate_user_credentials(u"testuser", u"WRONGPASSWORD", req)
    assert should_be_no_user is None


def test_authenticate_user_credentials_wrong_login_name(internal_authenticator, internal_user):
    req = MagicMock()
    should_be_no_user = internal_authenticator.authenticate_user_credentials(u"unknown user", u"test", req)
    assert should_be_no_user is None


def test_change_user_password(internal_authenticator, internal_user):
    req = MagicMock()
    internal_authenticator.change_user_password(internal_user, u"test", u"changedpw", req)


def test_change_user_password_oldpw_wrong(internal_authenticator, internal_user):
    req = MagicMock()
    with raises(WrongPassword):
        internal_authenticator.change_user_password(internal_user, u"WRONGPASSWORD", u"changedpw", req)


def test_create_user(internal_authenticator, internal_authenticator_info):
    name = "created_testuser"
    password = "password"
    user = internal_authenticator.create_user(name, password)
    assert user.login_name == name
    assert internal_authenticator.authenticate_user_credentials(name, password, {}) is user
