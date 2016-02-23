# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Migrate old version nodes to sqlalchemy-continuum tables
"""
from core import db, Node, File
import logging
from sqlalchemy import Integer
from sqlalchemy_continuum import versioning_manager, Operation
from sqlalchemy_continuum.utils import version_class


logg = logging.getLogger(__name__)
q = db.query

# fake query to initalize sqlalchemy-continuum
#q(Node).first()


def fix_versoning_attributes():
    """There are 3 ways to say 'there is no next node'. Fix it..."""
    s = db.session
    s.execute("UPDATE node SET system_attrs=jsonb_object_delete_keys(system_attrs, 'prev_id') WHERE system_attrs->>'prev_id' IN (id::text, '0')")
    s.execute("UPDATE node SET system_attrs=jsonb_object_delete_keys(system_attrs, 'next_id') WHERE system_attrs->>'next_id' IN (id::text, '0')")


def all_version_nodes():
    return q(Node).filter(Node.system_attrs.has_key(u"next_id"))


def create_alias_version(current_version_node, old_version_node):
    s = db.session
    Transaction = versioning_manager.transaction_cls
    tx = Transaction()
    version_id = int(old_version_node.system_attrs[u"version.id"])
    operation_type = Operation.INSERT if version_id == 1 else Operation.UPDATE
    TransactionMeta = versioning_manager.transaction_meta_cls
    tx.meta_relation[u"alias_id"] = TransactionMeta(key=u"alias_id", value=unicode(old_version_node.id))
    tx.meta_relation[u"tag"] = TransactionMeta(key=u"tag", value=u"v" + unicode(version_id))
    if u"version.comment" in old_version_node.system_attrs:
        tx.meta_relation[u"comment"] = TransactionMeta(key=u"comment", value=old_version_node.system_attrs[u"version.comment"])
    s.add(tx)
    NodeVersion = version_class(Node)
    NodeFileVersion = version_class(File)
    nv = NodeVersion(id=current_version_node.id,
                     name=old_version_node.name,
                     type=old_version_node.type,
                     schema=old_version_node.schema,
                     attrs=old_version_node.attrs,
                     orderpos=old_version_node.orderpos,
                     transaction=tx,
                     operation_type=operation_type)

    for fi in old_version_node.files:
        nfv = NodeFileVersion(nid=current_version_node.id,
                              path=fi.path,
                              mimetype=fi.mimetype,
                              filetype=fi.filetype,
                              operation_type=operation_type,
                              transaction=tx)
        db.session.add(nfv)

    db.session.add(nv)
    return nv


def create_current_version(current_version_node):
    s = db.session
    Transaction = versioning_manager.transaction_cls
    tx = Transaction()
    version_id = current_version_node.system_attrs[u"version.id"]
    operation_type = Operation.UPDATE
    TransactionMeta = versioning_manager.transaction_meta_cls
    tx.meta_relation[u"tag"] = TransactionMeta(key=u"tag", value=u"v" + unicode(version_id))

    if u"version.comment" in current_version_node.system_attrs:
        tx.meta_relation[u"comment"] = TransactionMeta(key=u"comment", value=current_version_node.system_attrs[u"version.comment"])

    s.add(tx)
    NodeVersion = version_class(Node)
    NodeFileVersion = version_class(File)
    nv = NodeVersion(id=current_version_node.id,
                     name=current_version_node.name,
                     type=current_version_node.type,
                     schema=current_version_node.schema,
                     attrs=current_version_node.attrs,
                     orderpos=current_version_node.orderpos,
                     transaction=tx,
                     operation_type=operation_type)

    for fi in current_version_node.files:
        nfv = NodeFileVersion(nid=current_version_node.id,
                              path=fi.path,
                              mimetype=fi.mimetype,
                              filetype=fi.filetype,
                              operation_type=operation_type,
                              transaction=tx)
        s.add(nfv)
    s.add(nv)
    s.flush()
    return nv


def insert_migrated_version_nodes(all_versioned_nodes):
    processed_nodes = set()

    for node in all_versioned_nodes:
        next_id = node.system_attrs.get(u"next_id")
        version_nodes = []
        while node and next_id:
            version_nodes.append(node)
            last_node_id = node.id
            node = q(Node).get(next_id)
            if node is None:
                logg.warn("node version with id %s, successor of version %s not found!", next_id, last_node_id)
            else:
                next_id = node.system_attrs.get(u"next_id")

        # node is the current version now, old versions in version_nodes
        if node and node.id not in processed_nodes:
            logg.info("current version %s, versions %s", node.id, [n.id for n in version_nodes])
            assert node.id > max(n.id for n in version_nodes)

            old_version = None
            for version_node in version_nodes:
                older_version, old_version = old_version, create_alias_version(node, version_node)
                if older_version is not None:
                    older_version.end_transaction_id = old_version.transaction_id

            current_version = create_current_version(node)
            old_version.end_transaction_id = current_version.transaction_id

            processed_nodes.add(node.id)

    return processed_nodes


def finish():
    s = db.session
    # delete version nodes and dependent information
    s.execute("DELETE FROM nodefile WHERE nid IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")
    s.execute("DELETE FROM nodemapping WHERE cid IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")
    s.execute("DELETE FROM nodemapping WHERE nid IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")
    s.execute("DELETE FROM node WHERE id IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")

    # insert remaining nodes as current version into version table
    # create a single transaction for all nodes, would be too much to create a transaction for each node ;)
    res = s.execute("INSERT INTO transaction DEFAULT VALUES RETURNING id")
    tx_id = res.fetchone()[0]
    stmt = ("INSERT INTO node_version (id, name, type, schema, attrs, orderpos, transaction_id, operation_type) " +
           "SELECT id, name, type, schema, attrs, orderpos, {}, {} " +
           "FROM node WHERE id NOT IN (SELECT id FROM node_version)")

    s.execute(stmt.format(tx_id, Operation.INSERT))
