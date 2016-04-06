#!/usr/bin/env python2
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
* users: migrate users and usergroups in mediatum schema
* dynusers: migrate users from dynauth plugin
* user_finish: rename migrated user nodes, migrate user home dirs and set admin user, rehash passwords
* versions: migrate node versions
* permissons: migrate node permissons from import schema to mediatum schema
* inherited_permissons: calculate inherited permissions
* everything: run all tasks above

Database changes are commited after all actions have been run.

"""
from __future__ import print_function

import configargparse
import logging
import os.path
import subprocess
import sys
import tempfile
sys.path.append(".")

from sqlalchemy_continuum import remove_versioning
from core import init, plugins
from collections import OrderedDict
from utils.postgres import vacuum_analyze_tables

LOG_FILEPATH = os.path.join(tempfile.gettempdir(), "mediatum_mysql_migrate.log")

init.basic_init(root_loglevel=logging.INFO, log_filepath=LOG_FILEPATH)
plugins.init_plugins()

import core.database.postgres
from core.database.postgres import db_metadata
from core.database.postgres.alchemyext import disable_triggers, enable_triggers
from core.database.postgres.connector import read_and_prepare_sql

core.database.postgres.SLOW_QUERY_SECONDS = 1000
logging.getLogger("migration.acl_migration").trace_level = logging.ERROR
logging.getLogger("core.database.postgres").trace_level = logging.ERROR

logg = logging.getLogger("mysql_migrate.py")

from core import db

s = db.session
q = db.query

MIGRATION_DIR = os.path.join(os.path.dirname(__file__), "../migration")

PGLOADER_BINARY = "pgloader"
DOCKER_PGLOADER_IMAGE = "dpausp/pgloader"


def pgloader():
    if args.docker:
        docker_call = ["docker", "run", "--rm", "-u", "{}:{}".format(os.getuid(), os.getgid()),
                       "-v", "{}:/tmp".format(os.path.abspath(MIGRATION_DIR))]
        links = []
        for link in args.link:
            links.append("--link")
            links.append(link)

        subprocess.call(docker_call + links + [DOCKER_PGLOADER_IMAGE, "pgloader", "/tmp/mysql_migration.load"])
    else:
        script_path = os.path.join(MIGRATION_DIR, "mysql_migration.load")
        subprocess.call([PGLOADER_BINARY, "--verbose", script_path])


def prepare_import_migration(s):
    for sql_file in ["migration.sql", "acl_migration.sql", "user_migration.sql"]:
        s.execute(read_and_prepare_sql(sql_file, MIGRATION_DIR))
    init.update_nodetypes_in_db()
    logg.info("finished db preparations")


def migrate_core(s):
    s.execute("SELECT mediatum.migrate_core()")
    logg.info("finished node + attrs, nodefile and nodemapping migration")


def users(s):
    s.execute("SELECT mediatum.clean_trash_dirs()")
    s.execute("SELECT mediatum.purge_empty_home_dirs()")
    s.execute("SELECT mediatum.migrate_usergroups()")
    s.execute("SELECT mediatum.migrate_internal_users()")
    logg.info("finished user migration")


def dynusers(s):
    s.execute("SELECT mediatum.migrate_dynauth_users()")
    logg.info("finished dynauth user migration")


def user_finish(s):
    s.execute("SELECT mediatum.rename_user_system_nodes()")
    # orphaned home dirs are moved to node 1276513
    from migration import user_migration
    user_migration.migrate_home_dirs(1276513)
    user_migration.migrate_special_dirs()
    user_migration.set_admin_group()
    user_migration.rehash_md5_password_hashes()


def versions(s):
    # we really must commit before running version migration or nodes created earlier will be lost
    s.commit()
    from migration import version_migration
    # all node classes must be defined for versioning, stub them if some plugins are missing, for example
    init.check_undefined_nodeclasses(stub_undefined_nodetypes=True)
    version_migration.fix_versioning_attributes()
    version_migration.insert_migrated_version_nodes(version_migration.all_version_nodes())
    version_migration.finish()
    remove_versioning()


def permissions(s):
    from migration import acl_migration
    init.check_undefined_nodeclasses(stub_undefined_nodetypes=True)
    acl_migration.migrate_access_entries()
    acl_migration.set_home_dir_permissions()
    acl_migration.migrate_rules()
    s.commit()
    s.execute("SELECT mediatum.deduplicate_access_rules()")
    logg.info("finished permissions migration")


def inherited_permissions(s):
    # we are using database functions here, so we must commit before continuing
    s.commit()
    vacuum_analyze_tables(s, db_metadata=db_metadata)
    try:
        s.execute("SELECT mediatum.create_all_inherited_access_rules_read()")
        s.execute("SELECT mediatum.create_all_inherited_access_rules_write()")
        s.execute("SELECT mediatum.create_all_inherited_access_rules_data()")
    except:
        s.execute("TRUNCATE mediatum.access_rule, mediatum.access_ruleset CASCADE")
        s.commit()
        raise

    logg.info("created inherited access rules")


def cleanup(s):
    s.execute("SELECT mediatum.delete_migrated_nodes()")


def schema_migration(s):
    prepare_import_migration(s)
    migrate_core(s)
    users(s)
    dynusers(s)
    user_finish(s)
    versions(s)
    permissions(s)
    inherited_permissions(s)


actions = OrderedDict([
    ("pgloader", pgloader),
    ("prepare", prepare_import_migration),
    ("core", migrate_core),
    ("users", users),
    ("dynusers", dynusers),
    ("user_finish", user_finish),
    ("versions", versions),
    ("permissions", permissions),
    ("inherited_permissions", inherited_permissions),
    ("cleanup", cleanup),
    ("schema_migration", schema_migration),
])

if __name__ == "__main__":
    parser = configargparse.ArgumentParser("mediaTUM mysql_migrate.py")
    parser.add_argument("--docker", default=False, action="store_true", help="use the prebuilt docker image for pgloader")
    parser.add_argument("--link", default=[], action="append", help="docker link to another container like: --link=postgres:postgres")
    parser.add_argument("action", nargs="*", choices=actions.keys())

    print()
    print("-" * 80)
    print()

    args = parser.parse_args()
    requested_actions = args.action

    s.execute("SET search_path to mediatum")
    s.commit()

    # pgloader can't be run in the action loop and must be run first
    if "pgloader" in requested_actions:
        pgloader()
        requested_actions.remove("pgloader")


    if requested_actions:
        try:
            disable_triggers()

            for action in requested_actions:
                actions[action](s)
                s.commit()
        finally:
            s.rollback()
            enable_triggers()
            s.commit()
