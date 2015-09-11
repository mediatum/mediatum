# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from web.services.export.handlers import struct2rss
from mock.mock import MagicMock
import time
from core.permission import get_or_add_everybody_rule
from core.database.postgres.permission import NodeToAccessRule

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