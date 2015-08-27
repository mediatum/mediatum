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

import ldap
import re

import core.users as users
from core import Node
import core.config as config
import core.usergroups as usergroups

import utils.date as date
import logging

from core.auth import Authenticator

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
ldap.set_option(ldap.OPT_REFERRALS, 0)


logg = logging.getLogger(__name__)


def tryAuth(searchfilter):
    count = 5
    while True:
        l = ldap.initialize(config.get("ldap.server"))
        l.simple_bind_s(config.get("ldap.username"), config.get("ldap.password"))

        ldap_result_id = l.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE, searchfilter, [config.get("ldap.user_login")])
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


def tryLogin(user_dn, password, searchfilter):
    while True:
        l2 = ldap.initialize(config.get("ldap.server"))
        try:
            l2.simple_bind_s(user_dn, password)
        except ldap.INVALID_CREDENTIALS:
            return None, None

        ldap_result_id = l2.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE,
                                   searchfilter, config.get("ldap.attributes").split(","))
        try:
            return l2.result(ldap_result_id, 0, timeout=5)
        except ldap.TIMEOUT:
            logg.info("timeout while authenticating user,  retrying...")
            continue
        else:
            return None, None


def _getAttribute(self, attrname, list, separator=" "):
    ret = ""
    if ustr(attrname) == "":
        return ""
    for attr in ustr(attrname).split(","):
        attr = attr.strip()
        if attr in list.keys():
            for i in list[attr]:
                ret += i + separator
    if ret.endswith(separator):
        ret = ret[:(len(separator) * (-1))]
    return ret.strip()


def createLDAPUser(data, uname):
    user = Node(uname, "user")
    user.set("lastname", _getAttribute(config.get("ldap.user_lastname"), data))
    user.set("firstname", _getAttribute(config.get("ldap.user_firstname"), data))
    user.set("email", _getAttribute(config.get("ldap.user_email"), data))
    user.set("organisation", _getAttribute(config.get("ldap.user_org"), data))
    user.set("comment", _getAttribute(config.get("ldap.user_comment"), data))
    user.set("identificator", _getAttribute(config.get("ldap.user_identificator"), data))
    user.set("ldapuser.creationtime", date.format_date())

    if user.get("lastname") != "" and user.get("firstname") != "":
        user.setName("%s %s" % (user.get("lastname"), user.get("firstname")))

    added_to_groups = 0
    for group in _getAttribute(config.get("ldap.user_group"), data, ",").split(","):
        if group != "" and not usergroups.existGroup(group):
            #res = usergroups.create_group(group, description="LDAP Usergroup", option="")
            #res.set("ldapusergroup.creationtime", date.format_date())
            logg.info("skipped creation of ldap user group: ", group)
            continue
        g = usergroups.getGroup(group)
        if g:
            g.addChild(user)
            added_to_groups += 1

    logg.info("created ldap user: ", uname)
    if not added_to_groups:
        logg.warn("created ldap user %r, %r not added to any group", uname, user.id)
    return user


def updateLDAPUser(data, user):
    if user.get("lastname") != _getAttribute(config.get("ldap.user_lastname"), data):
        user.set("lastname", _getAttribute(config.get("ldap.user_lastname"), data))

    if user.get("firstname") != _getAttribute(config.get("ldap.user_firstname"), data):
        user.set("firstname", _getAttribute(config.get("ldap.user_firstname"), data))

    if user.get("email") != _getAttribute(config.get("ldap.user_email"), data) and user.get("email") == "":
        user.set("email", _getAttribute(config.get("ldap.user_email"), data))

    if user.get("organisation") != _getAttribute(config.get("ldap.user_org"), data):
        user.set("organisation", _getAttribute(config.get("ldap.user_org"), data))

    if user.get("comment") != _getAttribute(config.get("ldap.user_comment"), data):
        user.set("comment", _getAttribute(config.get("ldap.user_comment"), data))

    if user.get("identificator") != _getAttribute(config.get("ldap.user_identificator"), data):
        user.set("identificator", _getAttribute(config.get("ldap.user_identificator"), data))

    for group in _getAttribute(config.get("ldap.user_group"), data, ",").split(","):
        if group != "" and not usergroups.existGroup(group):
            logg.info("during ldap user update: skipped creation of ldap user group: ", group)
            continue
        g = usergroups.getGroup(group)
        if g and g not in user.getParents():
            g.addChild(user)


class LDAPAuthenticator(Authenticator):

    def authenticate_user_credentials(self, login, password, request):
        if login.find("@") == -1 and config.get("ldap.user_url", "") != "":
            login += "@" + config.get("ldap.user_url", "")

        searchfilter = config.get("ldap.searchfilter").replace("[username]", login)

        result_type, auth_result_data = tryAuth(searchfilter)

        if result_type == ldap.RES_SEARCH_RESULT:
            if len(auth_result_data) > 0:
                result_type = ldap.RES_SEARCH_ENTRY
                auth_result_data = auth_result_data[0]
            else:
                return 0

        if result_type != ldap.RES_SEARCH_ENTRY:
            return 0

        user_dn = auth_result_data[0][0]

        result_type, login_result_data = tryLogin(user_dn, password, searchfilter)

        if (result_type == ldap.RES_SEARCH_RESULT and len(login_result_data) > 0):
            result_type = ldap.RES_SEARCH_ENTRY
            result_data = login_result_data[0]
        if (result_type != ldap.RES_SEARCH_ENTRY):
            return 0

        if result_data[0][0] == user_dn:
            userfolder = users.getExternalUserFolder("ldapuser")
            for user in userfolder.getChildren():
                if user.getName() == login or login in user.get("identificator").split(" "):
                    updateLDAPUser(result_data[0][1], user)  # update node information in mediatum
                    return 1

            # check if newly to be created ldap user would be added to groups in function createLDAPUser
            add_to_groups = 0
            for group in self._getAttribute(config.get("ldap.user_group"), result_data[0][1], ",").split(","):
                if group != "" and not usergroups.existGroup(group):
                    continue
                g = usergroups.getGroup(group)
                if g:
                    add_to_groups += 1

            # refuse login if user would not be added to groups (such a user would not have any benefit from been loged in)
            if not add_to_groups:
                return 0

            userfolder.addChild(createLDAPUser(result_data[0][1], login))  # add new user
            return 1

        return 0

    def stdPassword(self, user):
        return 0

    def getName(self):
        return "ldap user"

    def canChangePWD(self):
        return 0
