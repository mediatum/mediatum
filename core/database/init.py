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

from core import config
from core import User, UserGroup, AuthenticatorInfo
from core.systemtypes import *
from contenttypes import Collections, Home
from workflow.workflow import Workflows
from core.auth import INTERNAL_AUTHENTICATOR_KEY, create_password_hash


logg = logging.getLogger(u"database")


def init_database_values(s):
    """
    :type s: Session
    """

    # node tree setup
    root = Root(u"root", u"root", 1)
    metadatatypes = Metadatatypes(u"metadatatypes", u"metadatatypes", 3)
    workflows = Workflows(u"workflows", u"workflows", 4)
    mappings = Mappings(u"mappings", u"mappings", 9)
    collections = Collections(u"collections", u"collections", schema=u"collection", id=10)
    collections.attrs[u"label"] = u"Collections"
    home = Home(u"home", u"home", 11)
    searchmasks = Searchmasks(u"searchmasks", u"searchmasks", 15)
    schedules = Schedules(u"schedules", u"schedules", 16)

    root.children.extend([metadatatypes, workflows, mappings, collections, home, searchmasks, schedules])

    # finally, add node tree. All nodes will be added automatically
    s.add(root)
    logg.info(u"loaded initial values")

    # default users and groups setup
    # add internal authenticator
    auth_type, auth_name = INTERNAL_AUTHENTICATOR_KEY
    internal_auth = AuthenticatorInfo(id=0, auth_type=auth_type, name=auth_name)

    admin_hash, admin_salt = create_password_hash(config.get(u"user.default_admin_password", "xadmin1"))

    adminuser = User(login_name=config.get(u"user.adminuser", u"administrator"),
                     password_hash=admin_hash,
                     salt=admin_salt,
                     email=u"admin@mediatum",
                     authenticator_info=internal_auth
                     )

    guestuser = User(login_name=config.get(u"user.guestuser", u"guest"),
                     email=u"guest@mediatum",
                     authenticator_info=internal_auth
                     )

    admingroup = UserGroup(name=config.get(u"user.admingroup", u"administration"),
                           is_workflow_editor_group=True,
                           is_editor_group=True
                           )
    admingroup.users.append(adminuser)
    s.add(admingroup)
    guestgroup = UserGroup(name=u"guests")
    guestgroup.users.append(guestuser)
    s.add(guestgroup)
