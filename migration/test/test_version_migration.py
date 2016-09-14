# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy_continuum import Operation, versioning_manager, remove_versioning
from core import db
from core.test.factories import NodeFactory, FileFactory
from migration import version_migration
from core.database.postgres.file import NodeToFile
from migration.test.fixtures import first_version_node


def test_fix_versioning_attributes_prev(session):
    n1 = NodeFactory()
    n2 = NodeFactory()
    n3 = NodeFactory()
    session.flush()
    n1.system_attrs[u"prev_id"] = unicode(n1.id)
    n2.system_attrs[u"prev_id"] = u"0"
    n3.system_attrs[u"prev_id"] = u"9"
    session.flush()
    version_migration.fix_versioning_attributes()
    session.expire_all()
    assert u"prev_id" not in n1.system_attrs
    assert u"prev_id" not in n2.system_attrs
    assert u"prev_id" in n3.system_attrs


def test_fix_versioning_attributes_next(session):
    n1 = NodeFactory()
    n2 = NodeFactory()
    n3 = NodeFactory()
    session.flush()
    n1.system_attrs[u"next_id"] = unicode(n1.id)
    n2.system_attrs[u"next_id"] = u"0"
    n3.system_attrs[u"next_id"] = u"9"
    session.flush()
    version_migration.fix_versioning_attributes()
    session.expire_all()
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
    assert version.tag == u"3"
    assert version.comment == u"current"
    assert version.operation_type == Operation.UPDATE
    assert version.id == current_version_node.id
    assert_copied_attributes(version, current_version_node)


def test_create_alias_version(session, current_version_node, middle_version_node):
    session.flush()
    version = version_migration.create_alias_version(current_version_node, middle_version_node)
    assert version.tag == u"2"
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


class FixedMockQuery(list):
    
    def order_by(self, *args, **kwargs):
        return self


def test_insert_migrated_version_nodes(session, first_version_node, middle_version_node, current_version_node):
    session.flush()
    # create the old-style double linked list of version nodes
    first_version_node.system_attrs[u"next_id"] = unicode(middle_version_node.id)
    middle_version_node.system_attrs[u"prev_id"] = unicode(first_version_node.id)
    middle_version_node.system_attrs[u"next_id"] = unicode(current_version_node.id)
    current_version_node.system_attrs[u"prev_id"] = unicode(middle_version_node.id)
    processed_nodes = version_migration.insert_migrated_version_nodes(FixedMockQuery([first_version_node, middle_version_node]))
    assert current_version_node.id in processed_nodes
    # XXX: sqlalchemy-continuum creates a version by itself (can we disable this?), the migration should create 3
    assert current_version_node.versions.count() == 4

    for ver in current_version_node.versions:
        assert ver.version_parent is current_version_node
        
        
def test_create_file_version(monkeypatch, first_version_node, middle_version_node, current_version_node):
    from sqlalchemy_continuum import version_class
    from core import File
    NodeToFileVersion = version_class(NodeToFile)
    FileVersion = version_class(File)
    
    def _version_class(clz):
        if clz == NodeToFile:
            return NodeToFileVersion
        elif clz == File:
            return FileVersion
    
    monkeypatch.setattr(version_migration, "version_class", _version_class)
    
    Transaction = versioning_manager.transaction_cls
    remove_versioning()
    
    first = first_version_node
    middle = middle_version_node
    current = current_version_node


    first_files = [FileFactory()]
    first.files.extend(first_files)

    middle_files = [FileFactory()]
    middle.files.extend(middle_files)

    current_files = [FileFactory()]
    current.files.extend(current_files)

    transaction = Transaction()
    version_migration.create_file_versions(first, middle, transaction)

    transaction2 = Transaction()
    version_migration.create_file_versions(middle, current, transaction2)
    