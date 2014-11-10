# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import raises

# setup
from core.test.setup import setup_with_db
setup_with_db()

from core.test.asserts import assert_deprecation_warning
from core.test.fixtures import *


def test_getContainerChildren(some_node):
    container_children = assert_deprecation_warning(some_node.getContainerChildren)
    assert len(container_children) == 1
    assert container_children[0].name == "container"


def test_getType_container(container_node):
    type = assert_deprecation_warning(container_node.getType)
    assert type == container_node.type


def test_getContentType_container(container_node):
    content_type = assert_deprecation_warning(container_node.getContentType)
    assert content_type == "directory"


def test_getSchema_container(container_node):
    # containers must not have a getSchema method
    with raises(AttributeError):
        container_node.getSchema()