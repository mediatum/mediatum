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


logg = logging.getLogger("database")


def init_database_values(s):
    """
    :type s: Session
    """

    # node tree setup
    root = Root("Gesamtbestand", "root", 1)
    metadatatypes = Metadatatypes("metadatatypes", "metadatatypes", 3)
    workflows = Workflows("workflows", "workflows", 4)
    mappings = Mappings("mappings", "mappings", 9)
    collections = Collections("collections", "collections", 10)
    collections.attrs["label"] = "Gesamtbestand"
    home = Home("home", "home", 11)
    navigation = Navigation("navigation", "navigation", 12)
    navigation.attrs["label"] = "Kollektionen"
    searchmasks = Searchmasks("searchmasks", "searchmasks", 15)
    schedules = Schedules("schedules", "schedules", 16)

    root.children.extend([metadatatypes, workflows, mappings, collections,
                          home, navigation, searchmasks, schedules])

    # finally, add node tree. All nodes will be added automatically
    s.add(root)
    logg.info("loaded initial values")

    # default users and groups setup
    # add internal authenticator
    internal_auth = AuthenticatorInfo(id=0, auth_type="internal", name="internal")

    adminuser = User(login_name=config.get("user.adminuser", "Administrator"),
                     password_hash="226fa8e6cbb1f4e25019e2645225fd47",
                     email=u"admin@mediatum",
                     authenticator_info=internal_auth
                     )

    guestuser = User(login_name=config.get("user.guestuser", "Gast"),
                     email=u"guest@mediatum",
                     authenticator_info=internal_auth
                     )

    admingroup = UserGroup(name=config.get("user.admingroup", "Administration"),
                           is_workflow_editor_group=True,
                           is_editor_group=True
                           )
    admingroup.users.append(adminuser)
    s.add(admingroup)
    guestgroup = UserGroup(name="Gast")
    guestgroup.users.append(guestuser)
    s.add(guestgroup)
