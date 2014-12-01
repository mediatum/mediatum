# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core.test.asserts import assert_deprecation_warning


def test_getSchema(content_node):
    schema = assert_deprecation_warning(content_node.getSchema)
    assert schema == "testschema"
    
    
def test_getContentType_content(content_node):
    content_type = assert_deprecation_warning(content_node.getContentType)
    assert content_type == "document"
    

