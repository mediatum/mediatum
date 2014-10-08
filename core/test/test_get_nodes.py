# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging

# setup
from core.test.setup import setup_with_db
setup_with_db()

from core.test.asserts import assert_node
from core.test.fixtures import session_empty, session_default_data


logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def test_get_root(session_default_data):
    from core.systemtypes import Root
    q = session_default_data.query
    n = q(Root).one()
    assert_node(n,
                name="Gesamtbestand",
                type="root",
                schema=None)


def test_get_collections(session_default_data):
    from contenttypes import Collections
    q = session_default_data.query
    n = q(Collections).one()
    assert_node(n,
                name="collections",
                type="collections",
                schema=None,
                label="Gesamtbestand")


def test_get_usergroups(session_default_data):
    from core.systemtypes import UserGroups
    q = session_default_data.query
    n = q(UserGroups).one()
    assert_node(n,
                name="usergroups",
                type="usergroups",
                schema=None)


def test_get_metadatatypes(session_default_data):
    from core.systemtypes import Metadatatypes
    q = session_default_data.query
    n = q(Metadatatypes).one()
    assert_node(n,
                name="metadatatypes",
                type="metadatatypes",
                schema=None)


def test_get_workflows(session_default_data):
    from workflow.workflow import Workflows
    q = session_default_data.query
    n = q(Workflows).one()
    assert_node(n,
                name="workflows",
                type="workflows",
                schema=None)


def test_get_mappings(session_default_data):
    from core.systemtypes import Mappings
    q = session_default_data.query
    n = q(Mappings).one()
    assert_node(n,
                name="mappings",
                type="mappings",
                schema=None)


def test_get_home(session_default_data):
    from contenttypes import Home
    q = session_default_data.query
    n = q(Home).one()
    assert_node(n,
                name="home",
                type="home",
                schema=None)


def test_get_navigation(session_default_data):
    from core.systemtypes import Navigation
    q = session_default_data.query
    n = q(Navigation).one()
    assert_node(n,
                name="navigation",
                type="navigation",
                schema=None,
                label="Kollektionen")


def test_get_usergroup(session_default_data):
    from core.usergroup import UserGroup
    q = session_default_data.query
    usergroup_nodes = q(UserGroup).all()
    assert len(usergroup_nodes) == 2


def test_get_users(session_default_data):
    from core.users import Users
    q = session_default_data.query
    users_nodes = q(Users).all()
    assert len(users_nodes) == 2


def test_get_user(session_default_data):
    from core.user import User
    q = session_default_data.query
    user_nodes = q(User).all()
    assert len(user_nodes) == 2
