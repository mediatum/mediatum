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

from core import db, Node, User, UserGroup, UserToUserGroup
from core.auth import Authenticator
import core.config as config
from core.auth import AuthenticatorInfo
from utils.compat import iteritems


logg = logging.getLogger(__name__)
q = db.query

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
ldap.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
ldap.set_option(ldap.OPT_REFERRALS, 0)


class LDAPConfigError(Exception):
    pass


class LDAPAuthenticator(Authenticator):
    
    """Provide LDAP authentication. Multiple LDAPAuthenticators can be configured in mediatum.cfg like:

        [ldap_name]
        server=name.sub.example.com
        ...

        [ldap_name2]
        server=name2.example.com

        The config option authenticator_order could look like that:

        authenticator_order=internal|default,ldap|name,ldap|name2

        This prefers internal authentication. If that fails, the ldap authenticator with 'name' is tried and so on.

    TODO: Logging should include the name of the authenticator!
    """

    auth_type = u"ldap"

    def __init__(self, name, config_dict=None):
        """
        :param name: used as name of the Authenticator and as config prefix
        :param config_dict: optional config that is used instead of the global config file
        """
        Authenticator.__init__(self, name)
        self._configure(config_dict)

    def try_auth(self, searchfilter):
        count = 5
        # if proxyuser given as full DN, take that
        # otherwise assume cn as given and append configured basedn
        while True:
            l = ldap.initialize(self.server)
            l.simple_bind_s(self.bind_user, self.proxyuser_password)

            ldap_result_id = l.search(self.base_dn, ldap.SCOPE_SUBTREE, searchfilter, [])
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

    def try_login(self, user_dn, password, searchfilter):
        while True:
            l2 = ldap.initialize(self.server)
            try:
                l2.simple_bind_s(user_dn, password.encode("utf8"))
            except ldap.INVALID_CREDENTIALS:
                return None, None

            ldap_result_id = l2.search(self.base_dn, ldap.SCOPE_SUBTREE, searchfilter, self.attributes)
            try:
                return l2.result(ldap_result_id, 0, timeout=5)
            except ldap.TIMEOUT:
                logg.info("timeout while authenticating user,  retrying...")
                continue
            else:
                return None, None

    def get_user_data(self, data):
        return {attribute_name: data.get(ldap_fieldname)[0].decode("utf8") if data.get(ldap_fieldname) else None
                for attribute_name, ldap_fieldname in iteritems(self.user_attributes)}

    def get_ldap_group_names(self, data):
        all_groups = set()

        for group_attr in self.group_attributes:
            group_desc_list = data.get(group_attr)

            if group_desc_list is not None:
                if "," in group_desc_list[0]:
                    groups = set([group_dn.split(u",")[0][3:] for group_dn in group_desc_list])
                else:
                    groups = set(group_desc_list)

                all_groups.update(groups)

        return all_groups

    def update_groups_from_ldap(self, user, data):

        ldap_group_names = self.get_ldap_group_names(data)

        # remove authenticator-managed groups that are no longer present in LDAP
        for group_assoc in user.group_assocs:
            if group_assoc.managed_by_authenticator and group_assoc.usergroup.name not in ldap_group_names:
                user.group_assocs.remove(group_assoc)

        # add missing groups from LDAP if we have a mediaTUM usergroup with that name
        groups = q(UserGroup).filter(UserGroup.name.in_(ldap_group_names)).all()
        for group in groups:
            if group not in user.groups:
                user.group_assocs.append(UserToUserGroup(usergroup=group, managed_by_authenticator=True))

        return groups

    def add_ldap_user(self, data, uname, authenticator_info):
        """Creates LDAP user and adds it to the session if there's at least one group associated with that user.
        :returns: User or None if user was not added."""
        s = db.session
        user_data = self.get_user_data(data)
        user = User(can_change_password=False, active=True, authenticator_info=authenticator_info, **user_data)

        if not user.display_name:
            if user.lastname and user.firstname:
                user.display_name = u"{} {}".format(user.lastname, user.firstname)

        added_groups = self.update_groups_from_ldap(user, data)
        if added_groups:
            s.add(user)
            logg.info("created ldap user: %s", uname)
            return user

        # no groups found? Don't add user, return None
        logg.info("not creating LDAP user for login '%s' because there's no matching group for this user", user.login_name)

    def update_ldap_user(self, data, user):
        user_data = self.get_user_data(data)
        user.update(**user_data)
        self.update_groups_from_ldap(user, data)

    def authenticate_user_credentials(self, login, password, request=None):

        # empty passwords not allowed, don't even try to authenticate with that...
        if not password:
            logg.info("empty password for login name %s", login)
            return

        if "@" not in login and self.user_url:
            login += self.user_url

        searchfilter = self.searchfilter_template.replace("[username]", login)

        result_type, auth_result_data = self.try_auth(searchfilter)

        if result_type == ldap.RES_SEARCH_RESULT:
            if len(auth_result_data) > 0:
                result_type = ldap.RES_SEARCH_ENTRY
                auth_result_data = auth_result_data[0]
            else:
                logg.info("LDAP auth failed for login name %s", login)
                return

        if result_type != ldap.RES_SEARCH_ENTRY:
            logg.info("LDAP auth failed for login name %s", login)
            return

        user_dn = auth_result_data[0][0]
        auth_result_dict = auth_result_data[0][1]
        dir_id = auth_result_dict[self.user_login][0]

        result_type, login_result_data = self.try_login(user_dn, password, searchfilter)

        if (result_type == ldap.RES_SEARCH_RESULT and len(login_result_data) > 0):
            result_type = ldap.RES_SEARCH_ENTRY
            login_result_data = login_result_data[0]
        if (result_type != ldap.RES_SEARCH_ENTRY):
            logg.info("LDAP auth failed for login name %s", login)
            return

        if login_result_data[0][0] == user_dn:
            user = q(User).filter_by(
                login_name=dir_id.decode("utf8")).join(AuthenticatorInfo).filter_by(
                name=self.name,
                auth_type=LDAPAuthenticator.auth_type).scalar()

            if user is not None:
                # we already have an user object, update data
                if config.getboolean("config.readonly"):
                    logg.warn("cannot update existing user data for login name %s in read-only mode", login, trace=False)
                else:
                    self.update_ldap_user(login_result_data[0][1], user)
                    db.session.commit()

                logg.info("LDAP auth succeeded for known login name %s", login)
                return user
            else:
                data = login_result_data[0][1]
                authenticator_info = q(AuthenticatorInfo).filter_by(name=self.name, auth_type=LDAPAuthenticator.auth_type).scalar()
                user = self.add_ldap_user(data, login, authenticator_info)

                if config.getboolean("config.readonly"):
                    logg.warn("LDAP auth succeeded for login name %s, but cannot create user in read-only mode. Refusing login.", 
                              login, trace=False)
                    return 
                    
                # refuse login if no user was created (if no matching group was found)
                if user is not None:
                    db.session.commit()
                    logg.info("LDAP auth succeeded for login name %s, created new user", login)
                    return user
                else:
                    logg.info("LDAP auth succeeded for login name %s, but user does not have any groups. Refusing login.", login)

    def _configure(self, config_dict):
        if config_dict is not None:
            def get_config(key, optional=False):
                value = config_dict.get(key)
                if value is None and not optional:
                    raise LDAPConfigError("config value must be present: " + key)
                return value
        else:
            def get_config(key, optional=False):
                value = config.get(u"ldap_{}.{}".format(self.name, key))
                if value is None and not optional:
                    raise LDAPConfigError("config value must be present: " + key)
                return value

        proxyuser = get_config("proxyuser")
        user_url = get_config("user_url", optional=True)

        if user_url and not user_url[0] == "@":
            at_user_url = "@" + user_url
        else:
            at_user_url = user_url

        if "," not in proxyuser:
            if user_url is None:
                raise LDAPConfigError("config value user_url must be present")
            self.bind_user = proxyuser + at_user_url
        else:
            self.bind_user = proxyuser

        self.user_url = at_user_url
        self.base_dn = get_config("basedn")
        self.server = get_config("server")
        self.proxyuser_password = get_config("proxyuser_password")
        self.user_login = get_config("user_login")
        self.attributes = get_config("attributes", "").encode("utf8").split(",") + [self.user_login.encode("utf8")]
        self.group_attributes = [a.strip() for a in get_config("group_attributes", "").split(",")]
        self.searchfilter_template = get_config("searchfilter")

        self.user_attributes = {
            "login_name": self.user_login,
            "email": get_config("user_email", optional=True),
            "lastname": get_config("user_lastname", optional=True),
            "firstname": get_config("user_firstname", optional=True),
            "organisation": get_config("user_org", optional=True),
            "comment": get_config("user_comment", optional=True),
            "telephone": get_config("user_telephone", optional=True),
            "display_name": get_config("user_displayname", optional=True),
        }
