# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture
from core.ldapauth import LDAPAuthenticator
from core.test.factories import UserFactory, AuthenticatorInfoFactory
import ldap


fake_record = [['CN=testuser,OU=Users,OU=TEST,OU=TEST,DC=test,DC=example,DC=com',
                {'cn': ['testuser'],
                 'department': ['dep'],
                 'displayName': ['User, Test'],
                 'givenName': ['Test'],
                 'mail': ['testuser@example.com'],
                    'mail_adresses': ['testuser@example.com', '123@my.example.com'],
                    'memberOf': ['CN=RESOURCE,OU=Resources,OU=TEST,OU=TEST,DC=test,DC=example,DC=com',
                                 'CN=TESTGROUP,OU=Groups,OU=TEST,OU=TEST,DC=test,DC=example,DC=com'],
                    'sn': ['User'],
                    'telephoneNumber': ['+42 123456']}]]


class FakeLDAP(object):

    def search(self, base_dn, scope, searchfilter, attributes):
        if "unknown" in searchfilter:
            return 0
        return 1

    def simple_bind_s(self, user, password):
        if password == u"wrong" or user == u"unknown":
            raise ldap.INVALID_CREDENTIALS

    def result(self, result_id, _, timeout):
        if result_id == 1:
            return ldap.RES_SEARCH_ENTRY, fake_record

        return ldap.RES_SEARCH_RESULT, []


@fixture
def fake_ldap_record(monkeypatch):
    monkeypatch.setattr("core.ldapauth.ldap.initialize", lambda x: FakeLDAP())
    return fake_record


def test_authenticate_credentials_known_user(fake_ldap_record):
    expected = fake_ldap_record[0][1]
    auth_info = AuthenticatorInfoFactory(auth_type=u"ldap", name=u"ldap", id=1)
    user = UserFactory(login_name=u"testuser", authenticator_info=auth_info)
    authenticator = LDAPAuthenticator(u"ldap")
    ret = authenticator.authenticate_user_credentials(u"testuser", u"password")
    assert ret == user
    assert user.login_name == expected["cn"][0]
    assert user.display_name == expected["displayName"][0]
    assert user.email == expected["mail"][0]


def test_authenticate_credentials_unknown(fake_ldap_record):
    auth_info = AuthenticatorInfoFactory(auth_type=u"ldap", name=u"ldap", id=1)
    user = UserFactory(login_name=u"testuser", authenticator_info=auth_info)
    authenticator = LDAPAuthenticator(u"ldap")
    ret = authenticator.authenticate_user_credentials(u"unknown", u"password")
    assert ret is None
