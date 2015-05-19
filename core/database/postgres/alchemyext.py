# -*- coding: utf-8 -*-
"""
    SQLAlchemy extensions

    * new types
    * compiler extension

    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from warnings import warn

from sqlalchemy.ext import compiler
from sqlalchemy.sql import table
from sqlalchemy.sql.ddl import CreateTable, _CreateDropBase, DropTable, sort_tables
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.sql.type_api import UserDefinedType
from sqlalchemy.orm.dynamic import AppenderQuery
from core.database.postgres import DeclarativeBase, db_metadata
from utils.compat import string_types
from sqlalchemy import Table


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
