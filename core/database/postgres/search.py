# -*- coding: utf-8 -*-
"""
    Transform the search language representation into SQLAlchemy query objects.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from sqlalchemy import func as sqlfunc, Text, text
from core import config, db
from core.search.representation import AttributeMatch, FullMatch, SchemaMatch, FulltextMatch, AttributeCompare, TypeMatch, And, Or, Not
from core.database.postgres import func, DeclarativeBase, integer_pk, integer_fk, C
from sqlalchemy.dialects.postgresql.base import TSVECTOR
from core.database.postgres.node import Node


comparisons = {
    ">": (lambda l, r: l > r),
    "<": (lambda l, r: l < r),
    ">=": (lambda l, r: l >= r),
    "<=": (lambda l, r: l <= r),
    "=": (lambda l, r: l == r)
}

logg = logging.getLogger(__name__)


# postgres search language configuration
# XXX: maybe we could do that in the database so that an admin could change search parameters at runtime?
global default_languages
default_languages = None


def fts_config_exists(config_name):
    stmt = text("SELECT FROM pg_catalog.pg_ts_config WHERE cfgname = :config_name")
    return db.session.execute(stmt, {"config_name": config_name}).fetchone() is not None


def default_languages_from_config():
    default_languages = set()
    langs_from_config = config.get("search.default_languages", "simple").split(",")
    for lang in langs_from_config:
        if fts_config_exists(lang):
            default_languages.add(lang)
        else:
            logg.warn("postgres search config '%s' not found, ignored")

    if not default_languages:
        logg.warn("no valid postgres search configs found, using 'simple' config")
        default_languages.add("simple")

    return default_languages


class Fts(DeclarativeBase):

    __tablename__ = "fts"

    id = integer_pk()
    # XXX: we allow multiple search items with the same configuration
    # XXX: otherwise, we could use nid, config, searchtype as primary key
    # XXX: may change in the future
    nid = integer_fk(Node.id)
    config = C(Text)
    searchtype = C(Text)
    tsvec = C(TSVECTOR)


def _prepare_searchstring(op, searchstring):
    return op.join(searchstring.strip('"').strip().split())


def make_fts_expr_tsvec(languages, target, searchstring, op="|"):
    """Searches tsvector column. `target` should have a gin index.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type tsvector
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    languages = list(languages)
    prepared_searchstring = _prepare_searchstring(op, searchstring)
    ts_query = sqlfunc.to_tsquery(languages[0], prepared_searchstring)

    for language in languages[1:]:
        ts_query = ts_query.op("||")(sqlfunc.to_tsquery(language, prepared_searchstring))

    return target.op("@@")(ts_query)


def make_fts_expr(languages, target, searchstring, op="|"):
    """Searches fulltext column, building ts_vector on the fly.
    `target` must have a gin index built with an ts_vector or this will be extremly slow.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type text
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    languages = list(languages)
    prepared_searchstring = _prepare_searchstring(op, searchstring)
    tsvec = func.to_tsvector_safe(languages[0], target)

    for language in languages[1:]:
        tsvec = tsvec.op("||")(func.to_tsvector_safe(language, prepared_searchstring))

    return make_fts_expr_tsvec(languages, target, searchstring, op)


def make_config_searchtype_cond(languages, searchtypes):
    # we must repeat the language for all search types, because Postgres is to stupid to find the optimal plan without that ;)

    languages = list(languages)
    searchtypes = list(searchtypes)
    def make_searchtype_cond_for_language(lang):
        inner_cond = (Fts.config == lang) & (Fts.searchtype == searchtypes[0])

        for searchtype in searchtypes[1:]:
            inner_cond |= ((Fts.config == lang) & (Fts.searchtype == searchtype))

        return inner_cond

    cond = make_searchtype_cond_for_language(languages[0])

    for lang in languages[1:]:
        cond |= make_searchtype_cond_for_language(lang)

    return cond


def apply_searchtree_to_query(query, searchtree, languages=None):

    if languages is None:
        if not default_languages:
            global default_languages
            default_languages = default_languages_from_config()
        languages = default_languages

    def walk(n):
        from core import Node
        if isinstance(n, And):
            left, fts_left = walk(n.left)
            right, fts_right = walk(n.right)
            return left & right, fts_left or fts_right

        elif isinstance(n, Or):
            left, fts_left = walk(n.left)
            right, fts_right = walk(n.right)
            return left | right, fts_left or fts_right

        elif isinstance(n, AttributeMatch):
            return make_fts_expr(languages,
                                 Node.attrs[n.attribute].astext,
                                 n.searchterm), False

        elif isinstance(n, FulltextMatch):
            cond = make_fts_expr_tsvec(languages, Fts.tsvec, n.searchterm)
            cond &= make_config_searchtype_cond(languages, ['fulltext'])
            return cond, True

        elif isinstance(n, FullMatch):
            cond = make_fts_expr_tsvec(languages, Fts.tsvec, n.searchterm)
            cond &= make_config_searchtype_cond(languages, ['fulltext', 'attrs'])
            return cond, True

        elif isinstance(n, AttributeCompare):
            return comparisons[n.op](Node.attrs[n.attribute].astext, n.compare_to), False

        elif isinstance(n, TypeMatch):
            return Node.type == n.nodetype, False

        elif isinstance(n, SchemaMatch):
            return Node.schema == n.schema, False

        else:
            raise NotImplementedError(str(n))

    searchcond, need_fts_join = walk(searchtree)

    if need_fts_join:
        query = query.join(Fts)

    return query.filter(searchcond)
