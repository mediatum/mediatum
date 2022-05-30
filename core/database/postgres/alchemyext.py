# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-late

"""
    SQLAlchemy extensions

    * new types
    * compiler extension
"""

from __future__ import division
from __future__ import print_function

from functools import partial
import logging
from warnings import warn

from sqlalchemy.ext import compiler
from sqlalchemy.sql import table
from sqlalchemy.sql.ddl import CreateTable, _CreateDropBase, DropTable, sort_tables
from sqlalchemy.sql.elements import quoted_name, ClauseElement, _literal_as_text, Executable
from sqlalchemy.sql.type_api import UserDefinedType
from sqlalchemy.orm.dynamic import AppenderQuery
from core.database.postgres import DeclarativeBase, db_metadata
from utils.compat import string_types
from sqlalchemy import Table, bindparam, select, column
from sqlalchemy.orm import aliased, mapper
from decorator import contextmanager


logg = logging.getLogger(__name__)


class CreateView(_CreateDropBase):

    def __init__(self, element, selectable, on=None, bind=None):
        self.selectable = selectable
        super(CreateView, self).__init__(element, on, bind)


class DropView(_CreateDropBase):
    pass


@compiler.compiles(CreateView)
def visit_create_view(ddl_element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (ddl_element.element.fullname, compiler.sql_compiler.process(ddl_element.selectable))


@compiler.compiles(DropView)
def visit_drop_view(ddl_element, compiler, **kw):
    return "DROP VIEW %s" % (ddl_element.element.fullname)


def view(name, metadata, selectable):
    if metadata.schema:
        full_name = metadata.schema + "." + name
    else:
        full_name = name
    t = table(quoted_name(name, None))
    t.metadata = metadata
    t.fullname = full_name
    t.schema = quoted_name(metadata.schema, None)

    for c in selectable.c:
        c._make_proxy(t)

    CreateView(t, selectable).execute_at('after-create', metadata)
    DropView(t).execute_at('before-drop', metadata)
    return t


class DropTableCascade(_CreateDropBase):
    pass


@compiler.compiles(DropTableCascade)
def visit_drop_table_cascade(ddl_element, compiler, **kw):
    return "DROP TABLE IF EXISTS %s CASCADE" % (ddl_element.element.fullname)


# modified version of https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/Explain

class Explain(Executable, ClauseElement):

    def __init__(self, stmt, analyze=False, verbose=False):
        self.statement = _literal_as_text(stmt)
        self.analyze = analyze
        self.verbose = verbose
        # helps with INSERT statements
        self.inline = getattr(stmt, 'inline', None)


@compiler.compiles(Explain, 'postgresql')
def pg_explain(element, compiler, **kw):
    text = "EXPLAIN "
    if element.analyze:
        text += "ANALYZE "
    if element.verbose:
        text += "VERBOSE "
    text += compiler.process(element.statement, **kw)
    return text


def explain(query, session, analyze=False):
    lines = session.execute(Explain(query, analyze)).fetchall()
    return "\n".join(l[0] for l in lines)


def exec_sqlfunc(s, func):
    return s.execute(func).fetchone()[0]


class LenMixin(object):

    def __len__(self):
        warn("use query.count() instead", DeprecationWarning)
        return self.count()


class AppenderQueryWithLen(AppenderQuery, LenMixin):
    pass


class Daterange(UserDefinedType):

    """Represent the Postgres Daterange TYPE in SQLAlchemy"""

    def get_col_spec(self, **kw):
        return "daterange[]"


def map_function_to_mapped_class(function, mapped_cls, *argnames):
    """Creates an additional mapping from a database function to an existing mapped class.
    The resulting mapper can be used in queries like that:

    session.query(MappedFunction).params(arg1=3, arg2="test").first()
    """
    select_columns = [column(c) for c in mapped_cls.__table__.columns.keys()]
    stmt = select(select_columns).select_from(function(*[bindparam(arg) for arg in argnames]))
    primary_key_columns = [getattr(stmt.c, c.name) for c in mapped_cls.__table__.primary_key.columns]
    return mapper(mapped_cls, aliased(stmt), non_primary=True, primary_key=primary_key_columns)


def get_table_name(obj):
    if isinstance(obj, string_types):
        if "." in obj:
            return obj
        else:
            return "mediatum." + obj
    elif isinstance(obj, Table):
        return obj.fullname
    else:
        return obj.__table__.fullname


def get_table(obj):
    if isinstance(obj, DeclarativeBase):
        return obj.__table__
    elif isinstance(obj, string_types):
        if "." in obj:
            fullname = obj
        else:
            fullname = "mediatum." + obj
        return db_metadata.tables[fullname]
    else:
        return obj


def drop_tables(objs, cascade=False):
    """DROP (CASCADE) tables. `objs` can be a sequence of table names, tables or Declarative models """
    from core import db
    tables = [get_table(m) for m in objs]
    dropped = []
    drop_ddl = DropTableCascade if cascade else DropTable

    for table in reversed(sort_tables(tables)):
        if db.engine.dialect.has_table(db.session.connection(), table.name, schema=table.schema):
            db.session.execute(drop_ddl(table))
            dropped.append(table.fullname)
        else:
            logg.info("ignored missing table '%s' while dropping", table.fullname)

    return dropped


def create_tables(objs):
    """CREATE tables. `objs` can be a sequence of table names, tables or Declarative models """
    from core import db
    tables = [get_table(m) for m in objs]
    created = []

    for table in sort_tables(tables):
        if not db.engine.dialect.has_table(db.session.connection(), table.name, schema=table.schema):
            db.session.execute(CreateTable(table))
            created.append(table.fullname)
        else:
            logg.info("ignored existing table '%s' while creating", table.fullname)

    return created


def reverse_sorted_tables():
    return reversed(db_metadata.sorted_tables)


def recreate_tables(objs, cascade=False):
    """DROP (CASCADE) and CREATE tables. `objs` can be a sequence of table names, tables or Declarative models """
    dropped = drop_tables(objs, cascade)
    created = create_tables(objs)

    return dropped, created


def truncate_tables(table_fullnames=None):
    from core import db
    s = db.session
    if not table_fullnames:
        table_fullnames = [t.fullname for t in reverse_sorted_tables()]

    table_fullname_str = ",".join(table_fullnames)
    s.execute('TRUNCATE {} RESTART IDENTITY;'.format(table_fullname_str))
    logg.info("truncated %s", table_fullname_str)


def toggle_triggers(action, table_fullnames=None):
    from core import db
    s = db.session

    if not table_fullnames:
        table_fullnames = [t.fullname for t in reverse_sorted_tables()]
        logg.warning("%s user triggers for all tables", action)
    else:
        logg.warning("%s user triggers for tables: %s", action, table_fullnames)

    for fullname in table_fullnames:
        s.execute('ALTER TABLE {} {} TRIGGER USER;'.format(fullname, action.upper()))


enable_triggers = partial(toggle_triggers, "enable")
disable_triggers = partial(toggle_triggers, "disable")


@contextmanager
def disabled_triggers():
    disable_triggers()
    yield
    enable_triggers()
