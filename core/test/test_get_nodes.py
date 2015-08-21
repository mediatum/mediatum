# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture

from core import db
from core.test.asserts import assert_node
q = db.query


@fixture(autouse=True)
def default_data(default_data):
    return default_data


def test_get_root():
    from core.systemtypes import Root
    n = q(Root).one()
    assert_node(n,
                name="root",
                type="root",
                schema=None)


def test_get_collections():
    from contenttypes import Collections
    n = q(Collections).one()
    assert_node(n,
                name="collections",
                type="collections",
                schema="collection",
                label="Collections")


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
                schema="home")