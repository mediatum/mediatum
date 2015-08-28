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

from functools import partial
import logging
from pprint import pformat
import sys
import warnings
import pyaml
from collections import OrderedDict
sys.path.append(".")

from core import init
from core.database.postgres import db_metadata, mediatumfunc
import configargparse

init.basic_init(root_loglevel=logging.WARN)

logg = logging.getLogger("manage.py")
logg.setLevel(logging.INFO)

from utils.log import TraceLogger
TraceLogger.trace_level = logging.ERROR
logging.getLogger("database").setLevel(logging.INFO)

from core.database.init import init_database_values
from core import db, Node
import utils.search


s = db.session
q = db.query


global search_initialized
search_initialized = False

# utility functions
# XXX: could be moved to utils

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


def reverse_sorted_tables():
    return reversed(db_metadata.sorted_tables)


def truncate_tables(s, table_fullnames=None):
    if not table_fullnames:
        table_fullnames = [t.fullname for t in reverse_sorted_tables()]

    table_fullname_str = ",".join(table_fullnames)
    s.execute('TRUNCATE {} RESTART IDENTITY;'.format(table_fullname_str))
    logg.info("truncated %s", table_fullname_str)


def get_conn_with_autocommit(s):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        conn = s.connection().execution_options(isolation_level="AUTOCOMMIT")
    return conn


def run_maint_command_for_tables(command, s, table_fullnames=None):
    """Runs a maintenance postgres command on tables that must be run outside a transaction.
    Uses all tables if `table_fullnames` is None.
    :param s: session to use
    :param table_fullnames: sequence of schema-qualified table names or None.
    """
    # we can't run inside an (implicit) transaction, so we have to use autocommit mode
    conn = get_conn_with_autocommit(s)
    if not table_fullnames:
        table_fullnames = [t.fullname for t in reverse_sorted_tables()]

    for fullname in table_fullnames:
        cmd = command + " " + fullname
        logg.info(cmd)
        conn.execute(cmd)

    logg.info("completed %s", command)


reindex_tables = partial(run_maint_command_for_tables, "REINDEX TABLE")
vacuum_tables = partial(run_maint_command_for_tables, "VACUUM")
vacuum_analyze_tables = partial(run_maint_command_for_tables, "VACUUM ANALYZE")


def run_single_sql(stmt, s):
    # we can't run inside an (implicit) transaction, so we have to use autocommit mode
    conn = get_conn_with_autocommit(s)
    return conn.execute(stmt)


# subcommand handlers


def schema(args):
    action = args.action.lower()
    if action == "drop":
        drop_schema(s)
    elif action == "create":
        create_schema(s)
    elif action == "recreate":
        drop_schema(s)
        create_schema(s)


def data(args):
    action = args.action.lower()
    if action == "init":
        init_database_values(s)
    elif action == "truncate":
        truncate_tables(s)


def fulltext(args):
    nid_or_all = args.nid_or_all.lower()

    if nid_or_all == "all":
        import_count = utils.search.import_fulltexts(args.overwrite)
        logg.info("loaded fulltexts for %s nodes", import_count)
    else:
        nid = int(args.nid_or_all)
        node = q(Node).get(nid)
        if node is None:
            logg.warn("node # %s not found!", nid)
            return
        imported = utils.search.import_node_fulltext(node, args.overwrite)
        if imported:
            logg.info("loaded fulltext for node # %s", nid)
        else:
            logg.info("nothing imported for node # %s", nid)


def searchindex(args):
    global search_initialized
    if not search_initialized:
        init.init_fulltext_search()
        search_initialized = True

    action = args.action.lower()

    if action == "recreate":
        logg.info("recreating search indexes from node fulltexts...")
        s.execute(mediatumfunc.recreate_all_tsvectors_fulltext())
        logg.info("recreating search indexes from node attributes...")
        s.execute(mediatumfunc.recreate_all_tsvectors_attrs())
        logg.info("searchindex recreate finished")


def vacuum(args):
    action = args.action.lower() if args.action else None

    if action is None:
        vacuum_tables(s)
    elif action == "analyze":
        vacuum_analyze_tables(s)


def result_proxy_to_yaml(resultproxy):
    rows = resultproxy.fetchall()
    as_list = [OrderedDict(sorted(r.items(), key=lambda e:e[0])) for r in rows]
    formatted = pyaml.dumps(as_list)
    return formatted


def sql(args):
    # multiple args can be given if the user didn't quote the query
    stmt = " ". join(args.sql)
    res = run_single_sql(stmt, s)
    if res.returns_rows:
        if args.yaml:
            logg.info("got %s rows", res.rowcount)
        else:
            logg.info("result:\n%s", res.fetchall())

        print(result_proxy_to_yaml(res).strip())
    else:
        logg.info("finished, no results returned")


if __name__ == "__main__":
    parser = configargparse.ArgumentParser("mediaTUM manage.py")
    subparsers = parser.add_subparsers(title="subcommands", help="see manage.py <subcommand> --help for more info")

    schema_subparser = subparsers.add_parser("schema", help="create / drop database schema")
    schema_subparser.add_argument("action", choices=["drop", "create", "recreate"], help="recreate first runs 'drop', then 'create'")
    schema_subparser.set_defaults(func=schema)

    data_subparser = subparsers.add_parser("data", help="delete database data / load default values")
    data_subparser.add_argument("action", choices=["truncate", "init"], help="remove all data | load default values into empty database")
    data_subparser.set_defaults(func=data)

    vacuum_subparser = subparsers.add_parser("vacuum", help="run VACUUM on all tables")
    vacuum_subparser.add_argument("action", nargs="?", choices=["analyze"])
    vacuum_subparser.set_defaults(func=vacuum)

    fulltext_subparser = subparsers.add_parser("fulltext", help="import fulltext files into the database")
    fulltext_subparser.add_argument("--overwrite", "-o", action="store_true", help="overwrite existing fulltexts")
    fulltext_subparser.add_argument("nid_or_all", help="node id to load fulltext for or 'all'")
    fulltext_subparser.set_defaults(func=fulltext)

    searchindex_subparser = subparsers.add_parser("searchindex", help="manage full text search indexing")
    searchindex_subparser.add_argument("action", choices=["recreate"], help="recreate search index from node data")
    searchindex_subparser.set_defaults(func=searchindex)

    sql_subparser = subparsers.add_parser("sql", help="run a single SQL statement (use quotes if needed, for example if your query contains *)")
    sql_subparser.add_argument("--yaml", "-y", action="store_true", help="pretty yaml output")
    sql_subparser.add_argument("sql", nargs="+", help="SQL statement to execute")
    sql_subparser.set_defaults(func=sql)

    args = parser.parse_args()
    args.func(args)

    s.commit()
