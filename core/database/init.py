# -*- coding: utf-8 -*-
#  mediatum - a multimedia content repository
#
#  Copyright (C) 2014 Tobias Stenzel <tobias.stenzel@tum.de>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

logg = logging.getLogger(__name__)


def init_database_values(s, default_admin_password=None):
    from core import config
    from core import User, UserGroup, AuthenticatorInfo, AccessRule
    from core.systemtypes import Root, Metadatatypes, Mappings, Searchmasks
    from contenttypes import Collections, Home
    from workflow.workflow import Workflows
    from core.auth import INTERNAL_AUTHENTICATOR_KEY, create_password_hash
    from core.database.postgres.permission import NodeToAccessRule

    """
    :type s: Session
    """

    # every database must have an everybody rule
    everybody_rule = AccessRule()
    s.add(everybody_rule)

    # node tree setup
    root = Root(u"root", id=1)
    metadatatypes = Metadatatypes(u"metadatatypes", id=3)
    workflows = Workflows(u"workflows", id=4)
    mappings = Mappings(u"mappings", id=9)
    collections = Collections(u"collections", schema=u"collection", id=10)
    collections.attrs[u"label"] = u"Collections"
    collections.access_rule_assocs.append(NodeToAccessRule(ruletype=u"read", rule=everybody_rule))
    home = Home(u"home", id=11)
    searchmasks = Searchmasks(u"searchmasks", id=15)

    root.children.extend([metadatatypes, workflows, mappings, collections, home, searchmasks])

    # finally, add node tree. All nodes will be added automatically
    s.add(root)
    logg.info(u"loaded initial values")

    # default users and groups setup
    # add internal authenticator
    auth_type, auth_name = INTERNAL_AUTHENTICATOR_KEY
    internal_auth = AuthenticatorInfo(id=0, auth_type=auth_type, name=auth_name)

    default_admin_password = config.get(u"user.default_admin_password", default_admin_password)
    if default_admin_password:
        admin_hash, admin_salt = create_password_hash(default_admin_password)
    else:
        # admin user cannot login when no default_admin_password is set
        admin_hash, admin_salt = None, None

    adminuser = User(login_name=config.get(u"user.adminuser", u"admin"),
                     password_hash=admin_hash,
                     salt=admin_salt,
                     email=u"admin@mediatum",
                     authenticator_info=internal_auth,
                     can_change_password=True
                     )

    guestuser = User(login_name=config.get_guest_name(),
                     email=u"guest@mediatum",
                     authenticator_info=internal_auth
                     )

    admingroup = UserGroup(name=config.get(u"user.admingroup", u"administration"),
                           is_workflow_editor_group=True,
                           is_editor_group=True,
                           is_admin_group=True
                           )
    admingroup.users.append(adminuser)
    s.add(admingroup)
    guestgroup = UserGroup(name=u"guests")
    guestgroup.users.append(guestuser)
    s.add(guestgroup)
