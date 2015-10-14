# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import datetime
import json
import time
from mock.mock import MagicMock
from pytest import fixture
from web.services.export.handlers import struct2rss, struct2xml, struct2json, get_node_data_struct
from core.permission import get_or_add_everybody_rule
from core.database.postgres.permission import NodeToAccessRule
from schema.test.factories import MetadatatypeFactory


@fixture
def xml_fixture(parent_node, content_node):
    struct = {"nodelist": [parent_node, content_node],
              "build_response_start": time.time(),
              "status": "ok",
              "dataready": "0.1",
              "retrievaldate": datetime.datetime.now().isoformat(),
              "sortfield": "sortfield",
              "sortdirection": "up",
              "timetable": [],
              "result_shortlist": []}
    params = {}
    req = MagicMock()
    req.get_header = lambda x: "localhost:8081"
    req.fullpath = ""
    req.query = ""

    MetadatatypeFactory(name=u"directory")
    MetadatatypeFactory(name=u"testschema")

    return struct, req, params


def test_rss(container_node, other_container_node, content_node, collections, home_root, guest_user, root):

    everybody_rule = get_or_add_everybody_rule()

    root.children.append(collections)

    collections.access_rule_assocs.append(NodeToAccessRule(ruletype=u"read", rule=everybody_rule))
    collections.container_children.append(container_node)

    container_node.container_children.append(other_container_node)
    other_container_node.content_children.append(content_node)

    struct = {"nodelist": [other_container_node, content_node], "build_response_start": time.time()}
    params = {}
    req = MagicMock()
    req.get_header = lambda x: "localhost:8081"
    req.fullpath = ""
    req.query = ""

    res = struct2rss(req, "", params, None, struct=struct)
    print res
    # TODO: find some way to check XML content properly
    assert res.startswith("""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
<channel>""")
    assert "document/testschema" in res
    assert "http://localhost:8081/node?id=" in res


def test_xml_singlenode(xml_fixture):
    struct, req, params = xml_fixture
    xmlstr = struct2xml(req, "", params, None, singlenode=True, d=struct)
    print xmlstr
    assert "smallview mask not defined" in xmlstr
    assert "directory/directory" in xmlstr
    assert "![CDATA[7]]" in xmlstr


def test_xml_singlenode_send_children(xml_fixture):
    struct, req, params = xml_fixture
    xmlstr = struct2xml(req, "", params, None, singlenode=True, send_children=True, d=struct)
    print xmlstr
    assert "smallview mask not defined" in xmlstr
    assert "directory/directory" in xmlstr
    assert "document/testschema" in xmlstr
    assert "![CDATA[7]]" in xmlstr
    assert "![CDATA[8]]" in xmlstr


def test_xml(xml_fixture):
    struct, req, params = xml_fixture

    struct["nodelist_start"] = "10"
    struct["nodelist_limit"] = "10"
    struct["nodelist_countall"] = "100"

    xmlstr = struct2xml(req, "", params, None, singlenode=False, d=struct)
    print xmlstr
    assert "smallview mask not defined" in xmlstr
    assert "directory/directory" in xmlstr
    assert "![CDATA[7]]" in xmlstr


def test_json(xml_fixture):
    struct, req, params = xml_fixture
    n1, n2 = struct["nodelist"]

    jsonstr = struct2json(req, "", params, None, d=struct)
    print jsonstr
    res = json.loads(jsonstr)

    assert res["status"] == "ok"
    assert res["nodelist"] == [[{"id": n1.id}], [{"id": n2.id}]]


def test_search(guest_user, root, home_root, collections, container_node, content_node, other_container_node):
    params = {}
    params["q"] = "full=test"

    everybody_rule = get_or_add_everybody_rule()

    root.children.append(collections)

    collections.access_rule_assocs.append(NodeToAccessRule(ruletype=u"read", rule=everybody_rule))
    collections.container_children.append(container_node)

    container_node.container_children.append(other_container_node)
    other_container_node.content_children.append(content_node)

    req = MagicMock()
    req.get_header = lambda x: "localhost:8081"
    req.fullpath = ""
    req.query = ""

    res = get_node_data_struct(req, "", params, None, container_node.id)
    assert res["status"] == "ok"
    print res
    pass