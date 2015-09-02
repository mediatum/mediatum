"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner Neudenberger <neudenberger@ub.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
import ldap

from core import db, Node, User, UserGroup
from core.auth import Authenticator
import core.config as config
from core.auth import AuthenticatorInfo
from utils.compat import iteritems


logg = logging.getLogger(__name__)

q = db.query

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
ldap.set_option(ldap.OPT_REFERRALS, 0)

LDAP_BASE_DN = config.get("ldap.basedn")
LDAP_USER_LOGIN = config.get("ldap.user_login")
LDAP_SERVER = config.get("ldap.server")
LDAP_PROXYUSER = config.get("ldap.proxyuser")
LDAP_PROXYUSER_PASSWORD = config.get("ldap.proxyuser_password")
LDAP_USER_URL = config.get("ldap.user_url")
LDAP_USER_LOGIN = config.get("ldap.user_login")
LDAP_ATTRIBUTES = config.get("ldap.attributes", "").encode("utf8").split(",") + [LDAP_USER_LOGIN.encode("utf8")]
LDAP_USER_GROUP_ATTRS = [a.strip() for a in config.get("ldap.user_group", "").split(",")]

LDAP_USER_ATTRIBUTES = {
    "lastname": config.get("ldap.user_lastname"),
    "firstname": config.get("ldap.user_firstname"),
    "email": config.get("ldap.user_email"),
    "organisation": config.get("ldap.user_org"),
    "comment": config.get("ldap.user_comment"),
    "telephone": config.get("ldap.user_telephone"),
    "login_name": LDAP_USER_LOGIN,
    "display_name": config.get("ldap.user_displayname"),
}

if LDAP_USER_URL and LDAP_USER_URL.find("@") == -1:
    LDAP_USER_URL = "@" + LDAP_USER_URL

if "," not in LDAP_PROXYUSER:
    BIND_USER = LDAP_PROXYUSER + LDAP_USER_URL
else:
    BIND_USER = LDAP_PROXYUSER


def try_auth(searchfilter):
    count = 5
    # if proxyuser given as full DN, take that
    # otherwise assume cn as given and append configured basedn
    while True:
        l = ldap.initialize(LDAP_SERVER)
        l.simple_bind_s(BIND_USER, LDAP_PROXYUSER_PASSWORD)

        ldap_result_id = l.search(LDAP_BASE_DN, ldap.SCOPE_SUBTREE, searchfilter, [])
        try:
            return l.result(ldap_result_id, 0, timeout=5)

        except ldap.TIMEOUT:
            count += 1
            if count > 5:
                raise
            logg.warn("timeout while trying to connect to user database, retry %s", count)
            continue
        else:
            return None, None


def try_login(user_dn, password, searchfilter):
    while True:
        l2 = ldap.initialize(LDAP_SERVER)
        try:
            l2.simple_bind_s(user_dn, password)
        except ldap.INVALID_CREDENTIALS:
            return None, None

        ldap_result_id = l2.search(LDAP_BASE_DN, ldap.SCOPE_SUBTREE, searchfilter, LDAP_ATTRIBUTES)
        try:
            return l2.result(ldap_result_id, 0, timeout=5)
        except ldap.TIMEOUT:
            logg.info("timeout while authenticating user,  retrying...")
            continue
        else:
            return None, None


def get_user_data(data):
    return {attribute_name: data.get(ldap_fieldname)[0].decode("utf8") if data.get(ldap_fieldname) else None
            for attribute_name, ldap_fieldname in iteritems(LDAP_USER_ATTRIBUTES)}


def get_ldap_group_names(data):
    all_groups = set()

    for group_attr in LDAP_USER_GROUP_ATTRS:
        group_desc_list = data.get(group_attr)

        if group_desc_list is not None:
            if "," in group_desc_list[0]:
                groups = set([group_dn.split(u",")[0][3:] for group_dn in group_desc_list])
            else:
                groups = set(group_desc_list)

            all_groups.update(groups)

    return all_groups


def update_groups_from_ldap(user, data):

    ldap_group_names = get_ldap_group_names(data)

    # add group from LDAP if we have a mediaTUM usergroup with that name
    # groups must be deleted manually if a user is no longer member of a group!
    groups = q(UserGroup).filter(UserGroup.name.in_(ldap_group_names)).all()
    user.groups.extend(groups)
    return groups


def add_ldap_user(data, uname, authenticator_info):
    """Creates LDAP user and adds it to the session if there's at least one group associated with that user.
    :returns: User or None if user was not added."""
    s = db.session
    user_data = get_user_data(data)
    user = User(can_change_password=False, can_edit_shoppingbag=True, active=True, authenticator_info=authenticator_info, **user_data)

    if not user.display_name:
        if user.lastname and user.firstname:
            user.display_name = u"{} {}".format(user.lastname, user.firstname)

    added_groups = update_groups_from_ldap(user, data)
    if added_groups:
        s.add(user)
        logg.info("created ldap user: %s", uname)
        return user

    # no groups found? Don't add user, return None
    logg.info("not creating LDAP user for login '%s' because there's no matching group for this user", user.login_name)


def update_ldap_user(data, user):
    user_data = get_user_data(data)
    user.update(**user_data)
    update_groups_from_ldap(user, data)


class LDAPAuthenticator(Authenticator):

    auth_type = u"ldap"

    def __init__(self, name, configuration=None):
        self._configure(configuration)
        Authenticator.__init__(self, name)

    def authenticate_user_credentials(self, login, password, request=None):
        if "@" not in login and LDAP_USER_URL:
            login += LDAP_USER_URL

        searchfilter = config.get("ldap.searchfilter").replace("[username]", login)

        result_type, auth_result_data = try_auth(searchfilter)

        if result_type == ldap.RES_SEARCH_RESULT:
            if len(auth_result_data) > 0:
                result_type = ldap.RES_SEARCH_ENTRY
                auth_result_data = auth_result_data[0]
            else:
                return

        if result_type != ldap.RES_SEARCH_ENTRY:
            return

        user_dn = auth_result_data[0][0]
        auth_result_dict = auth_result_data[0][1]
        dir_id = auth_result_dict[LDAP_USER_LOGIN][0]

        result_type, login_result_data = try_login(user_dn, password, searchfilter)

        if (result_type == ldap.RES_SEARCH_RESULT and len(login_result_data) > 0):
            result_type = ldap.RES_SEARCH_ENTRY
            login_result_data = login_result_data[0]
        if (result_type != ldap.RES_SEARCH_ENTRY):
            return

        if login_result_data[0][0] == user_dn:
            user = q(User).filter_by(
                login_name=dir_id).join(AuthenticatorInfo).filter_by(
                name=self.name,
                auth_type=LDAPAuthenticator.auth_type).scalar()

            if user is not None:
                # we already have an user object, update data
                update_ldap_user(login_result_data[0][1], user)
                db.session.commit()
                return user
            else:
                data = login_result_data[0][1]
                authenticator_info = q(AuthenticatorInfo).filter_by(name=self.name, auth_type=LDAPAuthenticator.auth_type).scalar()
                user = add_ldap_user(data, login, authenticator_info)

                # refuse login if no user was created (if no matching group was found)
                if user is not None:
                    db.session.commit()
                    return user


    def _configure(self, configuration):
        pass
