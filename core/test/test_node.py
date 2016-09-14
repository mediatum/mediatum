# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging

from pytest import raises, fixture

# setup
from core import db
from core import Node
from contenttypes.container import Collection
from core.test.asserts import assert_deprecation_warning, assert_sorted, assert_deprecation_warning_allow_multiple
from core.test.factories import NodeFactory
from datetime import date
import datetime
from utils.date import format_date


legacy_methods = [
    Node.getChild,
    Node.addChild,
    Node.getParents,
    Node.getFiles,
    # Node.get,
    Node.getName,
    Node.removeAttribute,
    Node.getOrderPos,
    Node.setOrderPos,
    Node.getType,
    Node.getChildren,
    Node.getChildren,
]


@fixture(params=[
    Node.getParents,
    Node.getFiles,
    Node.getName,
    Node.getOrderPos,
    Node.getType,
    Node.getChildren])
def legacy_getter(request):
    return request.param


def test_attributes(some_node):
    assert some_node.attributes["testattr"] == "testvalue"
    assert some_node.attrs is some_node.attributes


def test_getChild(some_node):
    content_child = some_node.getChild(u"content")
    assert content_child.name == "content"
    assert content_child.parents[0] is some_node


def test_addChild(some_node):
    new_child = NodeFactory(name=u"new_child")
    num_children = some_node.children.count()
    new_child_returned = assert_deprecation_warning(some_node.addChild, new_child)
    assert new_child is new_child_returned
    assert len(some_node.children) == num_children + 1


def test_getParents(some_node):
    parents = some_node.getParents()
    assert len(parents) == 1


def test_getFiles(some_node_with_file):
    node = some_node_with_file
    assert len(node.getFiles()) == 1


def test_get(some_node):
    value = some_node.get("testattr", "default_value")
    assert value == "testvalue"


def test_get_default_value(some_node):
    value = some_node.get("missing", "default_value")
    assert value == "default_value"


def test_get_system_attr(some_node):
    value = some_node.get("system.testattr", "default_value")
    assert value == "system.testvalue"


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


def test_set_system_attr_overwrite(some_node):
    some_node.set("system.testattr", "system.newvalue")
    assert some_node.system_attrs["testattr"] == "system.newvalue"


def test_set_system_attr_new(some_node):
    num_attrs = len(some_node.attrs)
    num_system_attrs = len(some_node.system_attrs)
    some_node.set("system.newattr", "system.newvalue")
    assert len(some_node.attrs) == num_attrs
    assert len(some_node.system_attrs) == num_system_attrs + 1
    assert some_node.system_attrs["newattr"] == "system.newvalue"


def test_getName(some_node):
    assert some_node.getName() == some_node.name


def test_removeAttribute(some_node):
    num_attrs = len(some_node.attrs)
    assert_deprecation_warning(some_node.removeAttribute, "testattr")
    assert len(some_node.attrs) == num_attrs - 1


def test_removeAttribute_system(some_node):
    num_attrs = len(some_node.system_attrs)
    assert_deprecation_warning(some_node.removeAttribute, "system.testattr")
    assert len(some_node.system_attrs) == num_attrs - 1


def test_getOrderPos(some_node):
    assert some_node.getOrderPos() == 1


def test_setOrderPos(some_node):
    assert_deprecation_warning(some_node.setOrderPos, 2)
    assert some_node.orderpos == 2


def test_getChildren(some_node):
    children = list(some_node.getChildren())
    assert len(children) == 2
    assert children[0] is not children[1]


def test_getContentChildren(some_node):
    content_children = some_node.getContentChildren()
    assert len(content_children) == 1
    assert content_children[0].name == "content"


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


def test_legacy_getter_deprecation(some_node, legacy_getter):
    assert_deprecation_warning(legacy_getter, some_node)


def test_all_children_by_query(parent_node):
    q = db.query
    res = parent_node.all_children_by_query(q(Node).filter(Node.orderpos > 1)).all()
    for c in res:
        assert c.orderpos > 1


# test NodeAppenderQuery (parents / children / container_children / content_children)

# asc tests for all child queries, desc tests only for `children`

def test_children_sort_by_orderpos(child_query_for_some_node):
    should_be_sorted = assert_deprecation_warning(child_query_for_some_node.sort_by_orderpos)
    assert_sorted(list(should_be_sorted), key=lambda n: n.orderpos)


def test_children_sort_by_orderpos_desc(some_node_with_sort_children):
    should_be_sorted = assert_deprecation_warning(some_node_with_sort_children.children.sort_by_orderpos, reverse=True)
    assert_sorted(list(should_be_sorted), key=lambda n: n.orderpos, reverse=True)


def test_children_sort_by_name(child_query_for_some_node):
    should_be_sorted = assert_deprecation_warning(child_query_for_some_node.sort_by_name)
    assert_sorted(list(should_be_sorted), key=lambda n: n.name)


def test_children_sort_by_name_desc(some_node_with_sort_children):
    should_be_sorted = assert_deprecation_warning(some_node_with_sort_children.children.sort_by_name, direction="down")
    assert_sorted(list(should_be_sorted), key=lambda n: n.name, reverse=True)


def test_children_sort_by_fields(child_query_for_some_node):
    should_be_sorted = assert_deprecation_warning(child_query_for_some_node.sort_by_fields, "sortattr")
    assert_sorted(list(should_be_sorted), key=lambda n: n.attrs["sortattr"])


def test_children_sort_by_fields_desc(some_node_with_sort_children):
    should_be_sorted = assert_deprecation_warning(some_node_with_sort_children.children.sort_by_fields, "-sortattr")
    assert_sorted(list(should_be_sorted), key=lambda n: n.attrs["sortattr"], reverse=True)


# just test sort_by_name for parents, rest should work too, if all other tests pass ;)
def test_parents_sort_by_name(some_node_with_two_parents):
    should_be_sorted = assert_deprecation_warning(some_node_with_two_parents.parents.sort_by_name)
    assert_sorted(list(should_be_sorted), key=lambda n: n.name)


def test_children_getIDs(some_node):
    child_ids = assert_deprecation_warning_allow_multiple(some_node.content_children.getIDs, 5)
    assert len(child_ids) == 1
    assert isinstance(child_ids[0], int)


### attribute mutation on persistent nodes

def test_attribute_overwrite_all(some_node):
    s = db.session
    s.commit()
    attrs = some_node.attrs.copy()
    attrs["testattr"] = "newvalue"
    some_node.attrs = attrs
    s.commit()
    assert some_node.attrs["testattr"] == "newvalue"


def test_attribute_mutation(some_node):
    """some_node.attrs must be a `MutableDict` from SQLA"""
    s = db.session
    s.commit()
    some_node.attrs["testattr"] = "newvalue"
    s.commit()
    assert some_node.attrs["testattr"] == "newvalue"


def test_all_children_content_type(parent_node):
    q = db.query
    from contenttypes import Content
    all_content_children = parent_node.all_children_by_query(q(Content)).all()
    assert len(all_content_children) == 3
    some_node = parent_node.children[0]
    assert some_node.content_children[0] in all_content_children
    assert some_node.container_children[0].content_children[0] in all_content_children
    # this is a content node below another content node.
    # It's only found by all_children_by_query(), not by content_children_for_all_subcontainers.
    assert some_node.content_children[0].content_children[0] in all_content_children


def test_content_children_for_all_subcontainers(parent_node):
    all_content_children = parent_node.content_children_for_all_subcontainers.all()
    some_node = parent_node.children[0]
    assert some_node.content_children[0] in all_content_children
    assert some_node.container_children[0].content_children[0] in all_content_children
    # this is a content node below another content node. Must not be returned by content_children_for_all_subcontainers
    assert some_node.content_children[0].content_children[0] not in all_content_children


def test_content_children_for_all_subcontainers_subquery(some_node):
    q = db.query
    sub = some_node.content_children_for_all_subcontainers.subquery()
    qy = q(sub).select_from(sub).order_by(sub.c.name).limit(10)
    assert qy


def test_add_collection(collections):
    q = db.query
    c = Collection("testcollection")
    collections.container_children.append(c)


def test_data_get_class_for_typestring():
    from contenttypes import Data
    data_cls = Node.get_class_for_typestring("data")
    assert data_cls is Data


def test_updatetime_legacy(some_node):
    node = some_node
    formatted_date = format_date(datetime.datetime.now()) 
    node.attrs["updatetime"] =  formatted_date
    assert node.updatetime == formatted_date


def test_updateuser_legacy(some_node):
    node = some_node
    node.attrs["updateuser"] =  u"me"
    assert node.updateuser == u"me"
    

def test_updatetime(session, some_node):
    node = some_node
    session.flush()
    assert node.updatetime


