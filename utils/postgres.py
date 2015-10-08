# -*- coding: utf-8 -*-
"""
    Some project-independent helpers for SQLAlchemy + Postgres

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import text


def execute_sqltext_one(session, stmt, **bindparams):
    return session.execute(text(stmt).bindparams(**bindparams)).fetchone()


def execute_sqltext_scalar(session, stmt, **bindparams):
    return session.execute(text(stmt).bindparams(**bindparams)).fetchone()[0]


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

