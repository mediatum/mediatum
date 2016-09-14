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
from core.database.postgres.file import NodeToFile


logg = logging.getLogger(__name__)
q = db.query

# fake query to initalize sqlalchemy-continuum
#q(Node).first()


def fix_versioning_attributes():
    """There are 3 ways to say 'there is no next node'. Fix it..."""
    s = db.session
    s.execute("UPDATE node SET system_attrs=jsonb_object_delete_keys(system_attrs, 'prev_id') WHERE system_attrs->>'prev_id' IN (id::text, '0')")
    s.execute("UPDATE node SET system_attrs=jsonb_object_delete_keys(system_attrs, 'next_id') WHERE system_attrs->>'next_id' IN (id::text, '0')")


def reset_version_data():
    """Delete irrelevant version data created in the migration process before creating node versions"""
    s = db.session
    # XXX: continuum does not define foreign keys, so we cannot use CASCADE...
    s.execute("TRUNCATE nodemapping_version") # created by user_finish while fixing user special dirs
    s.execute("TRUNCATE transaction")


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
    tx.meta_relation[u"tag"] = TransactionMeta(key=u"tag", value=unicode(version_id))
    tx.meta_relation[u"mysql_migration"] = TransactionMeta(key=u"mysql_migration", value=u"migrated older node version")
    if u"version.comment" in old_version_node.system_attrs:
        tx.meta_relation[u"comment"] = TransactionMeta(key=u"comment", value=old_version_node.system_attrs[u"version.comment"])
    s.add(tx)
    NodeVersion = version_class(Node)
    nv = NodeVersion(id=current_version_node.id,
                     name=old_version_node.name,
                     type=old_version_node.type,
                     schema=old_version_node.schema,
                     attrs=old_version_node.attrs,
                     orderpos=old_version_node.orderpos,
                     transaction=tx,
                     operation_type=operation_type)

    s.add(nv)
    s.flush()
    return nv


def create_current_version(current_version_node):
    s = db.session
    Transaction = versioning_manager.transaction_cls
    tx = Transaction()
    version_id = current_version_node.system_attrs[u"version.id"]
    operation_type = Operation.UPDATE
    TransactionMeta = versioning_manager.transaction_meta_cls
    tx.meta_relation[u"tag"] = TransactionMeta(key=u"tag", value=unicode(version_id))
    tx.meta_relation[u"mysql_migration"] = TransactionMeta(key=u"mysql_migration", value=u"migrated current node version")

    if u"version.comment" in current_version_node.system_attrs:
        tx.meta_relation[u"comment"] = TransactionMeta(key=u"comment", value=current_version_node.system_attrs[u"version.comment"])

    s.add(tx)
    NodeVersion = version_class(Node)
    nv = NodeVersion(id=current_version_node.id,
                     name=current_version_node.name,
                     type=current_version_node.type,
                     schema=current_version_node.schema,
                     attrs=current_version_node.attrs,
                     orderpos=current_version_node.orderpos,
                     transaction=tx,
                     operation_type=operation_type)

    s.add(nv)
    s.flush()
    return nv


def create_file_versions(previous_node, node, current_version_node, transaction):
    """Create file and node_to_file version changes from diff between files of `previous_node` and `node`.
    `node` must be a the version node that follows `previous_node`.
    `current_version_node` is the newest version node following `previous_node` and `node`
    """
    
    NodeToFileVersion = version_class(NodeToFile)
    FileVersion = version_class(File)
    s = db.session
    
    new_files = set(node.files) - set(previous_node.files)
    removed_files = set(previous_node.files) - set(node.files)
    
    for fi in new_files:
        fv = FileVersion(id=fi.id,
                         path=fi.path,
                         mimetype=fi.mimetype,
                         filetype=fi.filetype,
                         operation_type=Operation.INSERT,
                         transaction=transaction)

        ntfv = NodeToFileVersion(nid=current_version_node.id, 
                                 file_id=fi.id,
                                 operation_type=Operation.INSERT,
                                 transaction=transaction)
        s.add(fv)
        s.add(ntfv)

    for fi in removed_files:
        fv = FileVersion(id=fi.id,
                         path=fi.path,
                         mimetype=fi.mimetype,
                         filetype=fi.filetype,
                         operation_type=Operation.DELETE,
                         transaction=transaction)
        
        # previous_file_version must be the file version with the highest transaction id
        previous_file_version = q(FileVersion).filter_by(id=fi.id).order_by(FileVersion.transaction_id.desc()).limit(1).scalar()
        if previous_file_version is not None:
            previous_file_version.end_transaction_id = transaction.id

        ntfv = NodeToFileVersion(nid=current_version_node.id, 
                                 file_id=fi.id,
                                 operation_type=Operation.DELETE,
                                 transaction=transaction)

        # previous_file_version must be the file version with the highest transaction id
        previous_node_to_file_version = (q(NodeToFileVersion).filter_by(nid=current_version_node.id, file_id=fi.id)
                                                             .order_by(NodeToFileVersion.transaction_id.desc()).limit(1).scalar())
        if previous_node_to_file_version is not None:
            previous_node_to_file_version.end_transaction_id = transaction.id
        s.add(fv)
        s.add(ntfv)


def insert_migrated_version_nodes(all_versioned_nodes):
    processed_node_ids = set()

    for node in all_versioned_nodes.order_by(Node.id):
        next_id = node.system_attrs.get(u"next_id")
        version_nodes = []
        # follow next_id to find newest (current) version for this node
        while node and next_id:
            version_nodes.append(node)
            last_node_id = node.id
            node = q(Node).get(next_id)
            if node is None:
                logg.warn("node version with id %s, successor of version %s not found!", next_id, last_node_id)
            else:
                next_id = node.system_attrs.get(u"next_id")

        # node is the current version now, old versions in version_nodes
        if node and node.id not in processed_node_ids:
            logg.info("current version %s, versions %s", node.id, [n.id for n in version_nodes])
            # node IDs were generated in insertion older, so older versions must have an ID lower than the ID of the current version
            assert node.id > max(n.id for n in version_nodes)

            old_version = None
            old_version_node = None
            for version_node in version_nodes:
                older_version, old_version = old_version, create_alias_version(node, version_node)
                older_version_node = old_version_node
                old_version_node = version_node
                
                if older_version is not None:
                    older_version.end_transaction_id = old_version.transaction_id
                    create_file_versions(older_version_node, old_version_node, node, old_version.transaction)
                    

            current_version = create_current_version(node)
            old_version.end_transaction_id = current_version.transaction_id
            create_file_versions(version_node, node, node, current_version.transaction)

            processed_node_ids.add(node.id)

    return processed_node_ids


def finish():
    s = db.session
    # delete version nodes and dependent information
    s.execute("DELETE FROM node_to_file WHERE nid IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")
    s.execute("DELETE FROM nodemapping WHERE cid IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")
    s.execute("DELETE FROM nodemapping WHERE nid IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")
    s.execute("DELETE FROM node WHERE id IN (SELECT CAST(value AS INTEGER) FROM transaction_meta WHERE key = 'alias_id')")

    # insert remaining nodes, files and node to file mappings as current version into version table
    # create a single transaction for all nodes, would be too much to create a transaction for each node ;)
    s.flush()
    res = s.execute("INSERT INTO transaction DEFAULT VALUES RETURNING id")
    tx_id = res.fetchone()[0]
    
    tx_meta_stmt = "INSERT INTO transaction_meta (transaction_id, key, value) VALUES ({tx_id}, 'mysql_migration', 'migrated unversioned nodes')"
    s.execute(tx_meta_stmt.format(tx_id=tx_id))
    
    node_stmt = ("INSERT INTO node_version (id, name, type, schema, attrs, orderpos, transaction_id, operation_type) " +
           "SELECT id, name, type, schema, attrs, orderpos, {}, {} " +
           "FROM node WHERE id NOT IN (SELECT id FROM node_version)")

    file_stmt = ("INSERT INTO file_version (id, path, filetype, mimetype, transaction_id, operation_type) " +
           "SELECT id, path, filetype, mimetype, {tx_id}, {optype} " +
           "FROM file WHERE id NOT IN (SELECT id FROM file_version)")

    node_to_file_stmt = ("INSERT INTO node_to_file_version (nid, file_id, transaction_id, operation_type) " +
           "SELECT nid, file_id, {tx_id}, {optype} " +
           "FROM node_to_file WHERE nid IN (SELECT id FROM node_version WHERE transaction_id={tx_id})")

    s.execute(node_stmt.format(tx_id, Operation.INSERT))
    s.execute(file_stmt.format(tx_id=tx_id, optype=Operation.INSERT))
    s.execute(node_to_file_stmt.format(tx_id=tx_id, optype=Operation.INSERT))
        
    # Reset issued_at times automatically set in the migration because saving the migration time 
    # will confuse code relying on the fact that issued_at is the time when the object / metadata was actually changed or created.
    s.execute("UPDATE transaction SET issued_at = NULL")
