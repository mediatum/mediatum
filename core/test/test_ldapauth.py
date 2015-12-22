# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture, raises
from core.ldapauth import LDAPAuthenticator, LDAPConfigError
from core.test.factories import UserFactory, AuthenticatorInfoFactory, UserGroupFactory
import ldap

BASE_DN = "OU=Users,OU=TEST,OU=TEST,DC=test,DC=example,DC=com"
USER_URL = "@example.com"

USER_DATA = {'cn': ['testuser'],
             'department': ['dep'],
             'displayName': ['User, Test'],
             'givenName': ['Test'],
             'mail': ['testuser' + USER_URL],
             'mail_adresses': ['testuser@example.com', '123@my.example.com'],
             'memberOf': ['CN=RESOURCE,OU=Resources,OU=TEST,OU=TEST,DC=test,DC=example,DC=com',
                          'CN=TESTGROUP,OU=Groups,OU=TEST,OU=TEST,DC=test,DC=example,DC=com'
                          'CN=NOTINMEDIATUM,OU=Groups,OU=TEST,OU=TEST,DC=test,DC=example,DC=com',],
             'sn': ['User'],
             'telephoneNumber': ['+42 123456']}

FAKE_RECORD = [['CN=testuser,' + BASE_DN, USER_DATA]]

LDAP_CONFIG = {
    "proxyuser": "proxyuser",
    "proxyuser_password": "proxyuser_password",
    "user_url": USER_URL,
    "basedn": BASE_DN,
    "server": "ldap.example.com",
    "user_login": "cn",
    "group_attributes": "memberOf,memberOf",
    "attributes": ",".join(USER_DATA.keys()),
    "searchfilter": "[username]",
    "user_displayname": "displayName",
    "user_email": "mail"
}


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
            return ldap.RES_SEARCH_ENTRY, FAKE_RECORD

        return ldap.RES_SEARCH_RESULT, []


@fixture
def fake_ldap_record(monkeypatch):
    monkeypatch.setattr("core.ldapauth.ldap.initialize", lambda x: FakeLDAP())
    return FAKE_RECORD


@fixture
def ldap_authenticator():
    return LDAPAuthenticator(u"ldap", LDAP_CONFIG)


def test_ldap_config_fail():
    with raises(LDAPConfigError):
        LDAPAuthenticator(u"ldap", {})


def test_authenticate_credentials_known_user(fake_ldap_record, ldap_authenticator):
    expected = fake_ldap_record[0][1]
    auth_info = AuthenticatorInfoFactory(auth_type=u"ldap", name=u"ldap", id=1)
    user = UserFactory(login_name=u"testuser", authenticator_info=auth_info)
    ret = ldap_authenticator.authenticate_user_credentials(u"testuser", u"password")
    assert ret == user
    assert user.login_name == expected["cn"][0]
    assert user.display_name == expected["displayName"][0]
    assert user.email == expected["mail"][0]


def test_authenticate_credentials_unknown(fake_ldap_record, ldap_authenticator):
    auth_info = AuthenticatorInfoFactory(auth_type=u"ldap", name=u"ldap", id=1)
    user = UserFactory(login_name=u"testuser", authenticator_info=auth_info)
    ret = ldap_authenticator.authenticate_user_credentials(u"unknown", u"password")
    assert ret is None


def test_get_ldap_group_names(fake_ldap_record, ldap_authenticator):
    group_names = ldap_authenticator.get_ldap_group_names(USER_DATA)
    assert group_names == set(["RESOURCE", "TESTGROUP"])


def test_update_groups_from_ldap(fake_ldap_record, ldap_authenticator):
    auth_info = AuthenticatorInfoFactory(auth_type=u"ldap", name=u"ldap", id=1)
    user = UserFactory(login_name=u"testuser", authenticator_info=auth_info)
    resource = UserGroupFactory(name="RESOURCE")
    testgroup = UserGroupFactory(name="TESTGROUP")
    # group NOTINMEDIATUM must not be added because it doesn't exist in the DB
    groups = ldap_authenticator.update_groups_from_ldap(user, USER_DATA)
    assert set(groups) == set([testgroup, resource])
    assert set(user.groups) == set(groups)
