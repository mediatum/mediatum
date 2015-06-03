# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

mediaTUM management script.

manage.py <action>

action is one of:

* create: create database schema and structure
* drop: drop database schema with all data
* recreate: run drop and create
* init: load initial database values needed for an empty mediaTUM
* truncate: deletes all data, but keeps the db structure

"""

from __future__ import division, absolute_import, print_function

import logging
import sys
from core.init import basic_init
from core.database.postgres import db_metadata
basic_init()

logg = logging.getLogger("manage.py")
# logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

from core.database.init import init_database_values
from core import db


def drop_schema(s):
    s.execute("DROP SCHEMA mediatum CASCADE")
    s.commit()
    logg.info("dropped database structure")


def create_schema(s):
    logg.info("creating DB schema...")

    s.execute("CREATE SCHEMA mediatum")
    s.commit()
    try:
        db.create_all()
        s.commit()
        logg.info("commited database structure")
    except:
        # I tried to use a transaction to enclose everything, but sqlalchemy (?) fails when the schema is created within the transaction
        # solution: just drop the schema it if something fails after schema creation
        s.execute("DROP SCHEMA mediatum CASCADE")
        raise


def truncate_tables(s):
    s.execute('TRUNCATE {} RESTART IDENTITY;'.format(
        ','.join(table.name
                 for table in reversed(db_metadata.sorted_tables))))


def vacuum_analyze_tables(s):
    conn = s.connection().execution_options(isolation_level="AUTOCOMMIT")
    for table in reversed(db_metadata.sorted_tables):
        cmd = 'VACUUM ANALYZE ' + table.fullname
        logg.info(cmd)
        conn.execute(cmd)


def reindex_tables(s):
    conn = s.connection().execution_options(isolation_level="AUTOCOMMIT")
    for table in reversed(db_metadata.sorted_tables):
        cmd = 'REINDEX TABLE ' + table.fullname
        logg.info(cmd)
        conn.execute(cmd)


s = db.session

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("no action specified! Actions: create drop recreate init truncate analyze_reindex")

    for action in sys.argv[1:]:

        if action == "create":
            create_schema(s)
    
        elif action == "drop":
            drop_schema(s)
    
        elif action == "recreate":
            drop_schema(s)
            create_schema(s)
    
        elif action == "init":
            logg.info("loading initial data...")
            init_database_values(s)
            s.commit()
            logg.info("commited initial data")
    
        elif action == "truncate":
            logg.info("truncating tables...")
            truncate_tables(s)
            s.commit()
            logg.info("commited table truncation")
    
        elif action == "analyze_reindex":
            vacuum_analyze_tables(s)
            reindex_tables(s)
            logg.info("vacuum analyze and reindex complete")
    
        else:
            raise Exception("unknown action: " + action)
