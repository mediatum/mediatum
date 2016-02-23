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


def test_fix_versioning_attributes_prev(session, some_node):
    n1 = NodeFactory()
    n2 = NodeFactory()
    n3 = NodeFactory()
    session.flush()
    n1.system_attrs["prev_id"] = unicode(n1.id)
    n2.system_attrs["prev_id"] = u"0"
    n3.system_attrs["prev_id"] = u"9"
    session.commit()
    version_migration.fix_versoning_attributes()
    session.commit()
    assert u"prev_id" not in n1.system_attrs
    assert u"prev_id" not in n2.system_attrs
    assert u"prev_id" in n3.system_attrs


def test_fix_versioning_attributes_next(session, some_node):
    n1 = NodeFactory()
    n2 = NodeFactory()
    n3 = NodeFactory()
    session.flush()
    n1.system_attrs["next_id"] = unicode(n1.id)
    n2.system_attrs["next_id"] = u"0"
    n3.system_attrs["next_id"] = u"9"
    session.commit()
    version_migration.fix_versoning_attributes()
    session.commit()
    assert u"next_id" not in n1.system_attrs
    assert u"next_id" not in n2.system_attrs
    assert u"next_id" in n3.system_attrs


def test_all_versioned_nodes():
    n1 = NodeFactory()
    n2 = NodeFactory()
    db.session.flush()
    n1.system_attrs["next_id"] = unicode(n2.id)
    n2.system_attrs["prev_id"] = unicode(n1.id)
    all_version_nodes = version_migration.all_version_nodes().all()
    assert n1 in all_version_nodes
    assert n2 not in all_version_nodes

