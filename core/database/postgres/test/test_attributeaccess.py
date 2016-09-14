# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.operators import like_op

from core.database.postgres.node import Node
from core.database.postgres.attributes import Attributes, AttributesExpressionAdapter, PythonicJSONElement


def test_attributes_init():
    node = Node("a")
    att = Attributes(node, "attrs")
    assert att.getter() == node.attrs


def test_attributes_init_persistent(some_node):
    node = some_node
    att = Attributes(node, "attrs")
    assert att.getter() == node.attrs


def test_a_object():
    node = Node("a")
    assert(isinstance(node.a, Attributes))


def test_a_expression():
    assert(isinstance(Node.a, AttributesExpressionAdapter))


def test_sys_object():
    node = Node("a")
    assert(isinstance(node.sys, Attributes))


def test_sys_expression():
    assert(isinstance(Node.sys, AttributesExpressionAdapter))


def test_a_getattr():
    expr = Node.a.attrname
    assert(isinstance(expr, PythonicJSONElement))
    assert(expr.left, Node.a)
    assert(expr.operator.opstring == "->")


def test_a_getattr_nested():
    expr = Node.a.deep.path.to.attribute
    assert(isinstance(expr, PythonicJSONElement))
    assert(expr.left, Node.a)
    assert(expr._path, ["deep", "path", "to", "attribute"])
    assert(expr.operator.opstring == "#>")


def test_a_getitem():
    expr = Node.a["attrname"]
    assert(expr._path == ["attrname"])


def test_a_getitem_nested():
    expr = Node.a["deep", "path", "to", "attribute"]
    assert(expr._path, ["deep", "path", "to", "attribute"])


def test_a_getattr_getitem_mix():
    expr = Node.a.deep["path"].to["attribute"]
    assert(expr._path, ["deep", "path", "to", "attribute"])

# Binary expression tests


def test_eq_string():
    expr = Node.a.attrname == "spam"
    assert(expr, BinaryExpression)
    assert(expr.right.effective_value == '"spam"')


def test_eq_int():
    expr = Node.a.height == 5
    assert(expr.right.effective_value == '5')


def test_eq_dict():
    expr = Node.a.dict == dict(a=5)
    assert(expr.right.effective_value == '{"a": 5}')


def test_eq_list():
    expr = Node.a.list == [1, 2]
    assert(expr.right.effective_value == '[1, 2]')


def test_like_string():
    expr = Node.a.string.like("%spam%")
    assert(expr.right.effective_value == '%spam%')
    assert(expr.operator == like_op)
    assert(expr.left.operator.opstring == '->>')


def test_query_with_a(session, some_node):
    node = some_node
    node["testattr"] = "test"
    assert session.query(Node).filter(Node.a.testattr == "test").scalar() == node


def test_query_with_sys(session, some_node):
    node = some_node
    node.system_attrs["testattr"] = "test"
    assert session.query(Node).filter(Node.sys.testattr == "test").scalar() == node


def test_query_with_a_differs_from_sys(session, some_node):
    node = some_node
    node["testattr"] = "test"
    node.system_attrs["testattr"] = "systest"
    assert session.query(Node).filter(Node.a.testattr == "systest").scalar() is None
    assert session.query(Node).filter(Node.sys.testattr == "test").scalar() is None
