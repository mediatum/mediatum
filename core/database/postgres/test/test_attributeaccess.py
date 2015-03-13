# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import fixture
from core.database.postgres.model import Node, Attributes, AttributesExpressionAdapter, PythonicJSONElement
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.operators import like_op

def test_a_object():
    node = Node("a")
    assert(isinstance(node.a, Attributes))


def test_a_expression():
    assert(isinstance(Node.a, AttributesExpressionAdapter))

    
### Binary expression tests
    
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
