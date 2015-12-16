# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from lxml import etree
from pytest import fixture

from core.xmlnode import add_node_to_xmldoc, create_xml_nodelist
from collections import OrderedDict

expected_simple = '<nodelist exportversion="1.1a">'\
+ '<node name="content" id="111" type="document/testschema" datatype="document" schema="testschema"><attribute name="sortattr"><![CDATA[6]]></attribute></node></nodelist>'

@fixture
def nodelist():
    return create_xml_nodelist()


def test_add_node_to_xmldoc_simple(session, nodelist, content_node):
    content_node.id = 111
    add_node_to_xmldoc(content_node, nodelist)
    assert etree.tostring(nodelist) == expected_simple


def test_add_node_to_xmldoc(nodelist, parent_node):
    add_node_to_xmldoc(parent_node, nodelist)
    xmlstr = etree.tostring(nodelist, pretty_print=True)
    # XXX: find a better way for XML assertions...
    assert "document/testschema" in xmlstr
    assert "directory/directory" in xmlstr
    assert "![CDATA[8]]" in xmlstr
