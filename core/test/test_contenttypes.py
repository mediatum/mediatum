# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core.test.asserts import assert_deprecation_warning
from contenttypes import Document, Data, Home, Collections
from workflow.workflow import Workflow


def test_getSchema(content_node):
    schema = assert_deprecation_warning(content_node.getSchema)
    assert schema == "testschema"


def test_getContentType_content(content_node):
    content_type = assert_deprecation_warning(content_node.getContentType)
    assert content_type == "document"


def test_data_get_all_subclasses():
    all_datatypes = Data.get_all_subclasses()
    assert len(all_datatypes) == 14
    assert Document in all_datatypes
    assert Collections in all_datatypes
    assert Home in all_datatypes
    assert Workflow not in all_datatypes


def test_data_get_all_datatypes():
    all_datatypes = Data.get_all_datatypes()
    assert len(all_datatypes) == 12
    assert Document in all_datatypes
    assert Collections not in all_datatypes
    assert Home not in all_datatypes
    assert Workflow not in all_datatypes
