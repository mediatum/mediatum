# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy_continuum import Operation
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
    n1.system_attrs[u"prev_id"] = unicode(n1.id)
    n2.system_attrs[u"prev_id"] = u"0"
    n3.system_attrs[u"prev_id"] = u"9"
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
    n1.system_attrs[u"next_id"] = unicode(n1.id)
    n2.system_attrs[u"next_id"] = u"0"
    n3.system_attrs[u"next_id"] = u"9"
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
    n1.system_attrs[u"next_id"] = unicode(n2.id)
    n2.system_attrs[u"prev_id"] = unicode(n1.id)
    all_version_nodes = version_migration.all_version_nodes().all()
    assert n1 in all_version_nodes
    assert n2 not in all_version_nodes


def assert_copied_attributes(version, node):
    for col in ("name", "type", "schema", "orderpos", "attrs"):
        assert getattr(version, col) is not None
        assert getattr(version, col) == getattr(node, col)


def test_create_current_version(session, current_version_node):
    session.flush()
    version = version_migration.create_current_version(current_version_node)
    assert version.tag == u"v3"
    assert version.comment == u"current"
    assert version.operation_type == Operation.UPDATE
    assert version.id == current_version_node.id
    assert_copied_attributes(version, current_version_node)


def test_create_alias_version(session, current_version_node, middle_version_node):
    session.flush()
    version = version_migration.create_alias_version(current_version_node, middle_version_node)
    assert version.tag == u"v2"
    assert version.comment == u"middle"
    assert version.operation_type == Operation.UPDATE
    assert version.transaction.meta.get(u"alias_id") == str(middle_version_node.id)
    assert version.id == current_version_node.id
    assert_copied_attributes(version, middle_version_node)


def test_create_alias_version_first(session, current_version_node, first_version_node):
    session.flush()
    version = version_migration.create_alias_version(current_version_node, first_version_node)
    assert version.operation_type == Operation.INSERT
    assert_copied_attributes(version, first_version_node)


def test_insert_migrated_version_nodes(session, current_version_node, middle_version_node, first_version_node):
    session.flush()
    # create the old-style double linked list of version nodes
    first_version_node.system_attrs[u"next_id"] = unicode(middle_version_node.id)
    middle_version_node.system_attrs[u"prev_id"] = unicode(first_version_node.id)
    middle_version_node.system_attrs[u"next_id"] = unicode(current_version_node.id)
    current_version_node.system_attrs[u"prev_id"] = unicode(middle_version_node.id)
    processed_nodes = version_migration.insert_migrated_version_nodes(version_migration.all_version_nodes())
    assert current_version_node.id in processed_nodes
    assert current_version_node.versions.count() == 3

    for ver in current_version_node.versions:
        assert ver.version_parent is current_version_node
