# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture

from core import db
from core.test.asserts import assert_node
from core.test.fixtures import default_data
q = db.query


# we need this fixture for all tests, so make it implicit
default_data = fixture(autouse=True)(default_data)


def test_get_root():
    from core.systemtypes import Root
    n = q(Root).one()
    assert_node(n,
                name="Gesamtbestand",
                type="root",
                schema=None)
    
    
def test_get_collections():
    from contenttypes import Collections
    n = q(Collections).one()
    assert_node(n,
                name="collections",
                type="collections",
                schema=None,
                label="Gesamtbestand")
         
         
def test_get_usergroups():
    from core.systemtypes import UserGroups
    n = q(UserGroups).one()
    assert_node(n,
                name="usergroups",
                type="usergroups",
                schema=None)
         
         
def test_get_metadatatypes():
    from core.systemtypes import Metadatatypes
    n = q(Metadatatypes).one()
    assert_node(n,
                name="metadatatypes",
                type="metadatatypes",
                schema=None)
         
         
def test_get_workflows():
    from workflow.workflow import Workflows
    n = q(Workflows).one()
    assert_node(n,
                name="workflows",
                type="workflows",
                schema=None)
         
         
def test_get_mappings():
    from core.systemtypes import Mappings
    n = q(Mappings).one()
    assert_node(n,
                name="mappings",
                type="mappings",
                schema=None)
         
         
def test_get_home():
    from contenttypes import Home
    n = q(Home).one()
    assert_node(n,
                name="home",
                type="home",
                schema=None)
         
         
def test_get_navigation():
    from core.systemtypes import Navigation
    n = q(Navigation).one()
    assert_node(n,
                name="navigation",
                type="navigation",
                schema=None,
                label="Kollektionen")
         
         
def test_get_usergroup():
    from core.usergroup import UserGroup
    usergroup_nodes = q(UserGroup).all()
    assert len(usergroup_nodes) == 2
         
         
def test_get_users():
    from core.users import Users
    users_nodes = q(Users).all()
    assert len(users_nodes) == 2
         
         
def test_get_user():
    from core.user import User
    user_nodes = q(User).all()
    assert len(user_nodes) == 2
