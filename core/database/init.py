# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os.path

import contenttypes as _contenttypes
import contenttypes.container as _
import core as _core
import core.auth as _
import core.permission as _
import core.systemtypes as _
import core.xmlnode as _
import core.database.postgres.permission as _
import core.database.postgres.user as _
from core import config as _core_config
import web as _web
import web.admin.adminutils as _
import workflow as _workflow
import workflow.workflow as _

logg = logging.getLogger(__name__)


def init_database_values(s, default_admin_password=None):
    """
    :type s: Session
    """

    # every database must have an everybody rule
    everybody_rule = _core.database.postgres.permission.AccessRule()
    s.add(everybody_rule)

    # node tree setup
    root = _core.systemtypes.Root(u"root", id=1)
    metadatatypes = _core.systemtypes.Metadatatypes(u"metadatatypes", id=3)
    workflows = _workflow.workflow.Workflows(u"workflows", id=4)
    mappings = _core.systemtypes.Mappings(u"mappings", id=9)
    collections = _contenttypes.container.Collections(u"collections", schema=u"collection", id=10)
    collections.attrs[u"label"] = u"Collections"
    collections.access_rule_assocs.append(_core.database.postgres.permission.NodeToAccessRule(
        ruletype=u"read",
        rule=everybody_rule,
        ))
    home = _contenttypes.container.Home(u"home", id=11)
    searchmasks = _core.systemtypes.Searchmasks(u"searchmasks", id=15)

    root.children.extend([metadatatypes, workflows, mappings, collections, home, searchmasks])

    # finally, add node tree. All nodes will be added automatically
    s.add(root)
    # activate menuitems metadatatypes, workflows etc.
    _web.admin.adminutils.adminNavigation()
    logg.info(u"loaded initial values")

    # default users and groups setup
    # add internal authenticator
    auth_type, auth_name = _core.auth.INTERNAL_AUTHENTICATOR_KEY
    internal_auth = _core.database.postgres.user.AuthenticatorInfo(id=0, auth_type=auth_type, name=auth_name)

    default_admin_password = _core_config.get(u"user.default_admin_password", default_admin_password)
    if default_admin_password:
        admin_hash, admin_salt = _core.auth.create_password_hash(default_admin_password)
    else:
        # admin user cannot login when no default_admin_password is set
        admin_hash, admin_salt = None, None

    adminuser = _core.database.postgres.user.User(
        login_name=_core_config.get(u"user.adminuser", u"admin"),
        password_hash=admin_hash,
        salt=admin_salt,
        email=u"admin@mediatum",
        authenticator_info=internal_auth,
        can_change_password=True,
        )

    guestuser = _core.database.postgres.user.User(
        login_name=_core_config.get_guest_name(),
        email=u"guest@mediatum",
        authenticator_info=internal_auth,
        )

    admingroup = _core.database.postgres.user.UserGroup(
        name=_core_config.get(u"user.admingroup", u"administration"),
        is_workflow_editor_group=True,
        is_editor_group=True,
        is_admin_group=True,
        )
    admingroup.users.append(adminuser)
    s.add(admingroup)
    guestgroup = _core.database.postgres.user.UserGroup(name=u"guests")
    guestgroup.users.append(guestuser)
    s.add(guestgroup)

    # add rules for admingroup, guestgroup
    for usergroup in [admingroup, guestgroup]:
        rule = _core.permission.get_or_add_access_rule(group_ids=[usergroup.id])
        ruleset = _core.database.postgres.permission.AccessRuleset(name=usergroup.name, description=usergroup.name)
        arr = _core.database.postgres.permission.AccessRulesetToRule(rule=rule)
        ruleset.rule_assocs.append(arr)

    # add example metadatatypes
    example_path_collection = os.path.join(_core_config.basedir, u"examples/content/collection.xml")
    with open(example_path_collection, "rb") as f:
        metadatatype_collection = _core.xmlnode.readNodeXML(f)

    example_path_directory = os.path.join(_core_config.basedir, u"examples/content/directory.xml")
    with open(example_path_directory, "rb") as f:
        metadatatype_directory = _core.xmlnode.readNodeXML(f)

    example_path_image = os.path.join(_core_config.basedir, u"examples/content/image.xml")
    with open(example_path_image, "rb") as f:
        metadatatype_image = _core.xmlnode.readNodeXML(f)

    example_path_document = os.path.join(_core_config.basedir, u"examples/content/document.xml")
    with open(example_path_document, "rb") as f:
        metadatatype_document = _core.xmlnode.readNodeXML(f)

    metadatatypes.children.extend([metadatatype_collection, metadatatype_directory, metadatatype_image,
                                   metadatatype_document])
