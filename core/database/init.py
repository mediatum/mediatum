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

from __future__ import absolute_import
import logging
from sqlalchemy.orm import Session
from core import config
from workflow.workflow import Workflows
from core.user import User
from core.usergroup import UserGroup

from core.systemtypes import *
from contenttypes import Collections, Home


logg = logging.getLogger("database")


def init_database_values(s):
    """
    :type s: Session
    """
    root = Root("Gesamtbestand", "root", 1)
    users = Users("users", "users", 2)
    metadatatypes = Metadatatypes("metadatatypes", "metadatatypes", 3)
    workflows = Workflows("workflows", "workflows", 4)
    usergroups = UserGroups("usergroups", "users", 5)
    mappings = Mappings("mappings", "mappings", 9)
    collections = Collections("collections", "collections", 10)
    collections.attributes["label"] = "Gesamtbestand"
    home = Home("home", "home", 11)
    navigation = Navigation("navigation", "navigation", 12)
    navigation.attributes["label"] = "Kollektionen"
    external_users = Users("external_users", "users", 14)
    root.children.extend([users, metadatatypes, workflows, usergroups, mappings, collections, home, navigation, external_users])

    adminuser = User(config.get("user.adminuser", "Administrator"), "user", 6)
    adminuser.attributes = {
        "password": "226fa8e6cbb1f4e25019e2645225fd47",
        "email": "admin@mediatum",
        "opts": "c"
    }
    guestuser = User(config.get("user.guestuser", "Gast"), "user", 7)
    guestuser.attributes["email"] = "guest@mediatum"
    users.children.extend([adminuser, guestuser])

    admingroup = UserGroup(config.get("user.admingroup", "Administration"), "usergroup", 8)
    admingroup.attributes["opts"] = "ew"
    admingroup.children.append(adminuser)
    guestgroup = UserGroup("Gast", "usergroup", 13)
    guestgroup.children.append(guestuser)
    usergroups.children.extend([admingroup, guestgroup])

    s.add(root)
    logg.info("loaded initial values")
