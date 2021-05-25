# -*- coding: utf-8 -*-
"""
    Some project-independent helpers for SQLAlchemy + Postgres

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division

import logging
import warnings
from functools import partial
from sqlalchemy import text

logg = logging.getLogger(__name__)


def reverse_sorted_tables(metadata):
    return reversed(metadata.sorted_tables)


def truncate_tables(s, table_fullnames=None, db_metadata=None):
    if not table_fullnames:
        if not db_metadata:
            raise ValueError("table_fullnames or db_metadata must be given!")

        table_fullnames = [t.fullname for t in reverse_sorted_tables(db_metadata)]

    table_fullname_str = ",".join(table_fullnames)
    s.execute('TRUNCATE {} RESTART IDENTITY CASCADE;'.format(table_fullname_str))
    logg.info("truncated %s", table_fullname_str)


def get_conn_with_autocommit(s):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        conn = s.connection().execution_options(isolation_level="AUTOCOMMIT")
    return conn


def execute_sqltext_one(session, stmt, **bindparams):
    return session.execute(text(stmt).bindparams(**bindparams)).fetchone()


def execute_sqltext_scalar(session, stmt, **bindparams):
    return session.execute(text(stmt).bindparams(**bindparams)).fetchone()[0]


def run_single_sql(stmt, session):
    # we can't run inside an (implicit) transaction, so we have to use autocommit mode
    conn = get_conn_with_autocommit(session)
    return conn.execute(stmt)


def schema_exists(session, schema_name):
    """Checks if `schema_name` is present in the database.
    :param session: SQLAlchemy session
    """
    stmt = "SELECT EXISTS (SELECT FROM information_schema.schemata WHERE schema_name=:schema_name)"
    schema_exists = execute_sqltext_scalar(session, stmt, schema_name=schema_name)
    return schema_exists


def table_exists(session, schema_name, table_name):
    """Checks if `table_name` is present in the database and `schema_name`.
    :param session: SQLAlchemy session
    """
    stmt = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema=:schema_name AND table_name=:table_name)"
    schema_exists = execute_sqltext_scalar(session, stmt, schema_name=schema_name, table_name=table_name)
    return schema_exists


def run_maint_command_for_tables(command, s, table_fullnames=None, db_metadata=None):
    """Runs a maintenance postgres command on tables that must be run outside a transaction.
    Uses all tables if `table_fullnames` is None.
    :param s: session to use
    :param table_fullnames: sequence of schema-qualified table names or None.
    """
    # we can't run inside an (implicit) transaction, so we have to use autocommit mode
    conn = get_conn_with_autocommit(s)
    if not table_fullnames:
        if not db_metadata:
            raise ValueError("table_fullnames or db_metadata must be given!")
        table_fullnames = [t.fullname for t in reverse_sorted_tables(db_metadata)]

    for fullname in table_fullnames:
        cmd = command + " " + fullname
        logg.info("%s", cmd)
        conn.execute(cmd)

    logg.info("completed %s", command)


reindex_tables = partial(run_maint_command_for_tables, "REINDEX TABLE")
vacuum_tables = partial(run_maint_command_for_tables, "VACUUM")
vacuum_analyze_tables = partial(run_maint_command_for_tables, "VACUUM ANALYZE")
vacuum_full_tables = partial(run_maint_command_for_tables, "VACUUM FULL")
