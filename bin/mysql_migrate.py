# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

mediaTUM MySQL to PostgreSQL migration.

mysql_migration.py <action>

Use 'everything' or run a selection of actions. The actions must be run in the given sequence!

action is one of:

* pgloader: migrate data from mysql DB to postgres import schema (edit config in migration/mysql_migration.load first!)
* prepare: prepare functions for data migration from import schema
* core: basic migrations from import schema to mediatum schema
* everything: run all tasks above

Database changes are commited after all actions have been run.

"""
from __future__ import print_function

import configargparse
import logging
import os.path
import subprocess
from core.init import basic_init
from core.database.postgres.connector import read_and_prepare_sql
from collections import OrderedDict
from bin.manage import vacuum_analyze_tables
basic_init()
import core.database.postgres


core.database.postgres.SLOW_QUERY_SECONDS = 1000
logging.getLogger("migration.acl_migration").trace_level = logging.ERROR
logging.getLogger("core.database.postgres").trace_level = logging.ERROR

logg = logging.getLogger("mysql_migrate.py")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARN)

from core import db

s = db.session

MIGRATION_DIR = os.path.join(os.path.dirname(__file__), "../migration")

PGLOADER_BINARY = "pgloader"


def pgloader(s=None):
    script_path = os.path.join(MIGRATION_DIR, "mysql_migration.load")
    subprocess.call([PGLOADER_BINARY, "--verbose", script_path])


def prepare_import_migration(s):
    for sql_file in ["migration.sql"]:
        s.execute(read_and_prepare_sql(sql_file, MIGRATION_DIR))
    logg.info("finished db preparations")


def migrate_core(s):
    s.execute("SELECT mediatum.migrate_core()")
    logg.info("finished node + attrs, nodefile and nodemapping migration")


def everything(s):
    pgloader()
    prepare_import_migration(s)
    migrate_core(s)


actions = OrderedDict([
    ("pgloader", pgloader),
    ("prepare", prepare_import_migration),
    ("core", migrate_core),
    ("everything", everything)
])

if __name__ == "__main__":
    parser = configargparse.ArgumentParser("mediaTUM mysql_migrate.py")
    parser.add_argument("--full-transaction", default=False, action="store_true")
    parser.add_argument("action", nargs="*", choices=actions.keys())

    print()
    print("-" * 80)
    print()

    args = parser.parse_args()

    for action in args.action:
        actions[action](s)
        if not args.full_transaction:
            logg.info("commit after action %s", action)
            s.commit()

    s.commit()
