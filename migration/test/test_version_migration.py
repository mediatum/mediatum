# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core import db
from migration.test.factories import ImportNodeFactory
from migration import version_migration
from migration.import_datamodel import NodeAttribute
from core.test.factories import NodeFactory

def test_all_versioned_nodes():
    n1 = NodeFactory()
    n2 = NodeFactory()
    db.session.flush()
    n1["system.next_id"] = unicode(n2.id)
    n2["system.prev_id"] = unicode(n1.id)
    all_version_nodes = version_migration.all_version_nodes().all()
    assert n1 in all_version_nodes
    assert n2 not in all_version_nodes

