# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging

# setup
from core.test.setup import setup_test_db
import warnings
from core.node import Node
from pytest import fixture
from _pytest.python import raises
setup_test_db()

from core.test.factories import NodeFactory

from core.test.asserts import assert_deprecation_warning
from core.test.fixtures import *

warnings.simplefilter("always")

legacy_methods = [
    Node.getChild,
    Node.addChild,
    Node.getParents,
    Node.getFiles,
    # Node.get,
    Node.getName,
    Node.removeAttribute,
    # Node.getAccess,
    # Node.setAccess,
    Node.getOrderPos,
    Node.setOrderPos,
    Node.getType,
    Node.getChildren,
    Node.getContainerChildren,
    Node.getContentType,
    Node.getChildren,
]


@fixture(params=[
    Node.getParents,
    Node.getFiles,
    Node.getName,
    Node.getOrderPos,
    Node.getType,
    Node.getContainerChildren,
    Node.getContentType,
    Node.getChildren])
def legacy_getter(request):
    return request.param

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


def test_attributes(some_node):
    assert some_node.attributes["testattr"] == "testvalue"
    assert some_node.attrs is some_node.attributes


def test_getChild(some_node):
    content_child = some_node.getChild("content")
    assert content_child.name == "content"
    assert content_child.parents[0] is some_node


def test_addChild(some_node):
    new_child = NodeFactory(name="new_child")
    num_children = some_node.children.count()
    new_child_returned = assert_deprecation_warning(some_node.addChild, new_child)
    assert new_child is new_child_returned
    assert len(some_node.children) == num_children + 1


def test_getParents(some_node):
    parents = some_node.getParents()
    assert len(parents) == 1


def test_getFiles(some_node):
    assert some_node.getFiles().count() == 1
    assert some_node.files[0].path == "testfile"


def test_get(some_node):
    value = some_node.get("testattr", "default_value")
    assert value == "testvalue"


def test_get_default_value(some_node):
    value = some_node.get("missing", "default_value")
    assert value == "default_value"


def test_set_overwrite(some_node):
    num_attrs = len(some_node.attrs)
    some_node.set("testattr", "newvalue")
    assert some_node.attrs["testattr"] == "newvalue"
    assert len(some_node.attrs) == num_attrs

def test_set_new(some_node):
    num_attrs = len(some_node.attrs)
    some_node.set("newattr", "newvalue")
    assert some_node.attrs["newattr"] == "newvalue"
    assert len(some_node.attrs) == num_attrs + 1


def test_getName(some_node):
    assert some_node.getName() == some_node.name


def test_removeAttribute(some_node):
    num_attrs = len(some_node.attrs)
    assert_deprecation_warning(some_node.removeAttribute, "testattr")
    assert len(some_node.attrs) == num_attrs - 1


def test_getAccess_read(some_node):
    read_access = assert_deprecation_warning(some_node.getAccess, "read")
    assert read_access == "read_access"


def test_getAccess_write(some_node):
    write_access = assert_deprecation_warning(some_node.getAccess, "write")
    assert write_access == "write_access"


def test_getAccess_data(some_node):
    data_access = assert_deprecation_warning(some_node.getAccess, "data")
    assert data_access == "data_access"


def test_setAccess_read(some_node):
    assert_deprecation_warning(some_node.setAccess, "read", "new_read_access")
    assert some_node.read_access == "new_read_access"


def test_setAccess_write(some_node):
    assert_deprecation_warning(some_node.setAccess, "write", "new_write_access")
    assert some_node.write_access == "new_write_access"


def test_setAccess_data(some_node):
    assert_deprecation_warning(some_node.setAccess, "data", "new_data_access")
    assert some_node.data_access == "new_data_access"


def test_getOrderPos(some_node):
    assert some_node.getOrderPos() == 1


def test_setOrderPos(some_node):
    assert_deprecation_warning(some_node.setOrderPos, 2)
    assert some_node.orderpos == 2


def test_getChildren(some_node):
    children = some_node.getChildren()
    assert len(children) == 2
    assert children[0] is not children[1]


def test_getContainerChildren(some_node):
    container_children = some_node.getContainerChildren()
    assert len(container_children) == 1
    assert container_children[0].name == "container"


def test_getContentChildren(some_node):
    content_children = some_node.getContentChildren()
    assert len(content_children) == 1
    assert content_children[0].name == "content"


def test_getContentType_content(content_node):
    assert content_node.getContentType() == "testschema"


def test_getContentType_container(container_node):
    assert container_node.getContentType() == "directory"


def test_legacy_getter_deprecation(some_node, legacy_getter):
    assert_deprecation_warning(legacy_getter, some_node)


def test_iter_raises_exception(some_node):
    with raises(TypeError):
        iter(some_node)


def test_node_nonzero(some_node):
    assert some_node


def test_setdefault_exists(some_node):
    ret = some_node.setdefault("testattr", "default_value")
    assert ret == "testvalue"


def test_setdefault_new(some_node):
    ret = some_node.setdefault("newattr", "default_value")
    assert ret == "default_value"
