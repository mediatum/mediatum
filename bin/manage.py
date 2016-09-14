#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

mediaTUM management script.

manage.py <subcommand> args...

see

* ``python bin/manage.py --help`` for details
* ``python bin/manage.py <subcommand> --help`` for details for a subcommand


"""
from collections import OrderedDict
from functools import partial
import logging
import os
import sys
import tempfile
import warnings
import pyaml
import sqlalchemy
from sqlalchemy_continuum import remove_versioning

sys.path.append(".")

from core import init
init.basic_init(prefer_config_filename="manage.cfg")

from core.database.postgres import db_metadata, mediatumfunc
from core.database.postgres.alchemyext import exec_sqlfunc, disable_triggers, enable_triggers
import configargparse

logg = logging.getLogger("manage.py")

from utils.log import TraceLogger
TraceLogger.trace_level = logging.ERROR

from core.database.init import init_database_values
from core import db, Node
import utils.search
import utils.iplist
from utils.postgres import truncate_tables, run_single_sql, vacuum_tables, vacuum_full_tables, vacuum_analyze_tables


s = db.session
q = db.query


global search_initialized
search_initialized = False


def import_dump(s, dump_filepath):
    disable_triggers()
    db.session.commit()
    db.run_psql_file(dump_filepath)
    enable_triggers()
    db.session.commit()
    logg.info("imported dump from %s", dump_filepath)


def _drop_index_for_attribute(name_or_all, index_type):
    from schema.schema import Metafield

    drop_func = getattr(mediatumfunc, "drop_attrindex_" + index_type)

    if name_or_all == "all":
        # find all search / sort metafields
        if index_type == "search":
            flags = "%s%"
        elif index_type == "sort":
            flags = "%o%"

        metafield_names = (t[0] for t in q(Metafield.name).filter(Metafield.a.opts.like(flags)).distinct())
        dropped_indices = []
        failed_indices = []

        for attrname in metafield_names:
            try:
                created = exec_sqlfunc(s, drop_func(attrname))
            except sqlalchemy.exc.OperationalError:
                logg.exception("failed to drop %s index for %s", index_type, attrname)
                s.rollback()
                failed_indices.append(attrname)
            else:
                if created:
                    s.commit()
                    dropped_indices.append(attrname)

        logg.info("dropped %s indices for %s attributes, %s failed: %s",
                  index_type, len(dropped_indices), len(failed_indices), failed_indices)
    else:
        name = name_or_all
        dropped = exec_sqlfunc(s, drop_func(name))
        if dropped:
            s.commit()
            logg.info("dropped %s index for attribute '%s'", index_type, name)
        else:
            logg.info("%s index for attribute '%s' does not exist, ignoring", index_type, name)


def _create_index_for_attribute(name_or_all, index_type, recreate=False):
    from schema.schema import Metafield

    creation_func = getattr(mediatumfunc, "create_attrindex_" + index_type)

    if name_or_all == "all":
        # find all search / sort metafields
        if index_type == "search":
            flags = "%s%"
        elif index_type == "sort":
            flags = "%o%"

        metafield_names = (t[0] for t in q(Metafield.name).filter(Metafield.a.opts.like(flags)).distinct())
        created_indices = []
        failed_indices = []

        for attrname in metafield_names:
            try:
                created = exec_sqlfunc(s, creation_func(attrname, recreate))
            except sqlalchemy.exc.OperationalError:
                logg.exception("failed to create %s index for %s", index_type, attrname)
                s.rollback()
                failed_indices.append(attrname)
            else:
                if created:
                    s.commit()
                    created_indices.append(attrname)

        logg.info("created %s indices for %s attributes, %s failed: %s",
                  index_type, len(created_indices), len(failed_indices), failed_indices)
    else:
        name = name_or_all
        created = exec_sqlfunc(s, creation_func(name, recreate))
        if created:
            s.commit()
            logg.info("created %s index for attribute '%s'", index_type, name)
        else:
            logg.info("%s index for attribute '%s' already exists", index_type, name)


# subcommand handlers

def schema(args):
    action = args.action.lower()
    if action == "drop":
        db.drop_schema()
    elif action == "create":
        db.create_schema()
    elif action == "recreate":
        db.drop_schema()
        db.create_schema()
    elif action == "upgrade":
        db.upgrade_schema()


def data(args):
    action = args.action.lower()
    if action == "init":
        init_database_values(s)
    elif action == "truncate":
        truncate_tables(s, db_metadata=db_metadata)
    elif action == "import":
        import_dump(s, args.sql_dumpfile)


def attrindex(args):
    name_or_all = args.name_or_all
    index_type = args.type

    if args.action == "drop":
        if index_type == "all":
            _drop_index_for_attribute(name_or_all, "search")
            _drop_index_for_attribute(name_or_all, "sort")
        else:
            _drop_index_for_attribute(name_or_all, index_type)

    else:
        recreate = args.action == "recreate"
        if index_type == "all":
            _create_index_for_attribute(name_or_all, "search", recreate)
            _create_index_for_attribute(name_or_all, "sort", recreate)
        else:
            _create_index_for_attribute(name_or_all, index_type, recreate)


def fulltext(args):
    # we must initialize all node types to import fulltexts
    init.full_init()

    nid_mod_or_all = args.nid_mod_or_all.lower()

    remove_versioning()

    if nid_mod_or_all == "all":
        import_count = utils.search.import_fulltexts(args.overwrite)
        logg.info("loaded fulltexts for %s nodes", import_count)
    elif nid_mod_or_all.startswith("mod"):
        mod_n, mod_i = [int(x) for x in nid_mod_or_all.split(" ")[1:]]
        import_count = utils.search.import_fulltexts(args.overwrite, mod_n, mod_i)
        logg.info("loaded fulltexts for %s nodes with id mod %s == %s", import_count, mod_n, mod_i)
        
    else:
        nid = int(nid_mod_or_all)
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

    index_type = args.type

    action = args.action.lower()

    if action == "recreate":

        if index_type in ("all", "attrs"):
            logg.info("recreating search indices from node attributes...")
            s.execute(mediatumfunc.recreate_all_tsvectors_attrs())

        if index_type in ("all", "fulltext"):
            logg.info("recreating search indices from node fulltexts...")
            s.execute(mediatumfunc.recreate_all_tsvectors_fulltext())

        logg.info("searchindex recreate finished")



def vacuum(args):
    action = args.action.lower() if args.action else None

    if action is None:
        vacuum_tables(s, db_metadata=db_metadata)
    elif action == "analyze":
        vacuum_analyze_tables(s, db_metadata=db_metadata)
    elif action == "full":
        vacuum_full_tables(s, db_metadata=db_metadata)


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


def iplist_import(args):
    f = open(args.file, "r") if args.file else sys.stdin
    try:
        addr = utils.iplist.ipranges_to_ipobjects(f)
        utils.iplist.update_mediatum_iplist(unicode(args.name), addr)
    finally:
        if args.file:
            f.close()


def main():
    parser = configargparse.ArgumentParser("mediaTUM manage.py")
    subparsers = parser.add_subparsers(title="subcommands", help="see manage.py <subcommand> --help for more info")

    schema_subparser = subparsers.add_parser("schema", help="create / drop database schema")
    schema_subparser.add_argument("action", choices=["drop", "create", "recreate", "upgrade"],
                                  help="recreate first runs 'drop', then 'create' | upgrade schema to newest revision")
    schema_subparser.set_defaults(func=schema)

    data_subparser = subparsers.add_parser("data", help="delete database data / load default values")
    data_subparser.add_argument("action", choices=["truncate", "init", "import"],
                                help="remove all data | load default values | import SQL dump into empty database")
    data_subparser.add_argument("sql_dumpfile", nargs="?", help="dump file to load for 'import' command")
    data_subparser.set_defaults(func=data)

    attrindex_subparser = subparsers.add_parser("attrindex", help="database performance index management")
    attrindex_subparser.add_argument("--type", "-t", choices=["search", "sort", "all"], default="all",
                                     help="which index type to create (search / sort / all)")
    attrindex_subparser.add_argument("action", choices=["create", "recreate", "drop"],
                                     help="drop / create / recreate search / sort index for attribute (or all attributes)")
    attrindex_subparser.add_argument("name_or_all", help="attribute name to index or all")
    attrindex_subparser.set_defaults(func=attrindex)

    vacuum_subparser = subparsers.add_parser("vacuum", help="run VACUUM on all tables")
    vacuum_subparser.add_argument("action", nargs="?", choices=["analyze", "full"])
    vacuum_subparser.set_defaults(func=vacuum)

    fulltext_subparser = subparsers.add_parser("fulltext", help="import fulltext files into the database")
    fulltext_subparser.add_argument("--overwrite", "-o", action="store_true", help="overwrite existing fulltexts")
    fulltext_subparser.add_argument("nid_mod_or_all", help="node ID, 'all' or 'mod n i' to partition the list of node IDs")
    fulltext_subparser.set_defaults(func=fulltext)

    searchindex_subparser = subparsers.add_parser("searchindex", help="manage full text search indexing")
    searchindex_subparser.add_argument("action", choices=["recreate"], help="recreate search index from node data")
    searchindex_subparser.add_argument("--type", "-t", choices=["fulltext", "attrs", "all"], default="all",
                                     help="which index type to create (fulltext / attrs / all)")
    searchindex_subparser.set_defaults(func=searchindex)

    sql_subparser = subparsers.add_parser(
        "sql",
        help="run a single SQL statement (use quotes if needed, for example if your query contains *)")
    sql_subparser.add_argument("--yaml", "-y", action="store_true", help="pretty yaml output")
    sql_subparser.add_argument("sql", nargs="+", help="SQL statement to execute")
    sql_subparser.set_defaults(func=sql)

    iplist_subparser = subparsers.add_parser("iplist", help="import ip-ranges (given as text file) into an ip ACL list")
    iplist_subparser.add_argument("name", help="Name of the ip list to be (re)written")
    iplist_subparser.add_argument("file", nargs="?", help="File to be parsed (will be stdin if none is given)")
    iplist_subparser.set_defaults(func=iplist_import)

    args = parser.parse_args()
    args.func(args)

    s.commit()


if __name__ == "__main__":
    main()
