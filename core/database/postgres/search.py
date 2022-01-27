# -*- coding: utf-8 -*-
"""
    Transform the search language representation into SQLAlchemy query objects.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import itertools as _itertools
import operator as _operator

import logging
from sqlalchemy import func, Index as _Index

import utils.utils as _utils
import utils.locks as _locks
from core.database.postgres import DB_SCHEMA_NAME as _DB_SCHEMA_NAME
from core import db
from core.search import SearchQueryException
from core.search.config import get_default_search_languages
from core.search.representation import AttributeMatch, FullMatch, SchemaMatch, FulltextMatch, AttributeCompare, TypeMatch, And, Or
from core.database.postgres.node import Node


comparisons = {
    ">": _operator.gt,
    "<": _operator.lt,
    ">=": _operator.ge,
    "<=": _operator.le,
    "eq": _operator.eq,
}

logg = logging.getLogger(__name__)


def set_session_timeout(session_timeout):
    """
    set session timeout
    for security reason the session is also set to readonly
    :param session_timeout: session timeout in seconds
    :return:
    """
    db.session.execute("SET transaction_read_only=true")
    db.session.execute("SET statement_timeout={}".format(session_timeout * 1000))


def _rewrite_prefix_search(t):
    # .* is stripped because some users try to use regex-like syntax. 
    # Just removing it should lead to better results in most cases.
    term_without_leading_wildcard = t.lstrip(u".*")
    if not term_without_leading_wildcard:
        # term is empty without wildcards, ignore it
        return 
    
    starpos = term_without_leading_wildcard.find(u"*")
    
    if starpos == -1:
        # we removed all stars from the beginning, it's not a wildcard search anymore
        return term_without_leading_wildcard
    
    return term_without_leading_wildcard[:starpos] + u":*"


_escape_postgres_ts_replacements = tuple(z.split() for z in (
    u'\\ \\\\',
    u"& \&",
    u"| \|",
    u"! \!",
    u": \:",
    u'" \"',
    u'( \(',
    u') \)',
    u'< \<',
    u'> \>',
    u"' \\'",
   ))

def _escape_postgres_ts_operators(t):
    for x,y in _escape_postgres_ts_replacements:
        t = t.replace(x,y)
    return t


def _prepare_searchstring(op, searchstring):
    searchstring_cleaned = searchstring.strip().strip('"').strip()
    terms = searchstring_cleaned.split()
    # escape chars with special meaning in postgres tsearch
    terms = _itertools.imap(_escape_postgres_ts_operators,terms)
    # Postgres needs the form term:* for prefix search, we allow simple stars at the end of the word
    terms = (_rewrite_prefix_search(t) if u"*" in t else t for t in terms)
    rewritten_searchstring = op.join(_itertools.ifilter(None,terms))

    if not rewritten_searchstring:
        raise SearchQueryException("invalid query for postgres full text search: " + searchstring)

    return rewritten_searchstring


def _make_languages_tsquery(languages, searchstring, op):
    """
    Prepares a `tsquery` expression to be used
    in the construction of search expressions.
    :param languages: postgresql language string
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    prepared_searchstring = _prepare_searchstring(op, searchstring)

    mk_query = lambda lang: func.to_tsquery(lang, prepared_searchstring)
    ts_queries = _itertools.imap(mk_query, languages)
    return reduce(lambda query1, query2: query1.op("||")(query2), ts_queries)


def make_fulltext_expr_tsvec(languages, searchstring, op="&"):
    """Searches fulltext column. fulltext should have a gin index.
    :param languages: postgresql language string
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    ts_query = _make_languages_tsquery(languages, searchstring, op)
    mk_cond = lambda lang: func.to_tsvector_safe(lang, Node.fulltext).op("@@")(ts_query)
    conds = _itertools.imap(mk_cond, languages)
    return reduce(lambda cond1, cond2: cond1.op("or")(cond2), conds)


def _make_attrs_expr_tsvec(languages, searchstring, op="&"):
    """Searches attrs column. attrs should have a gin index.
    :param languages: postgresql language string
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    ts_query = _make_languages_tsquery(languages, searchstring, op)
    mk_cond = lambda lang: func.jsonb_object_values_to_tsvector(lang, Node.attrs).op("@@")(ts_query)
    conds = _itertools.imap(mk_cond, languages)
    return reduce(lambda cond1, cond2: cond1.op("or")(cond2), conds)


def _make_fts_expr_tsvec(languages, target, searchstring, op="&"):
    """Searches tsvector column. `target` should have a gin index.
    :param languages: postgresql language string
    :param target: SQLAlchemy expression with type tsvector
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    ts_query = _make_languages_tsquery(languages, searchstring, op)
    return target.op("@@")(ts_query)


def _make_attribute_fts_cond(languages, target, searchstring, op="&"):
    """Searches fulltext column, building ts_vector on the fly.
    `target` must have a gin index built with an ts_vector or this will be extremly slow.
    :param languages: postgresql language string
    :param target: SQLAlchemy expression with type text
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    prepared_searchstring = _prepare_searchstring(op, searchstring)

    def cond_func(lang):
        tsvector = func.to_tsvector(lang, func.replace(target, ";", " "))
        tsquery = func.to_tsquery(lang, prepared_searchstring)
        return tsvector.op("@@")(tsquery)

    conds = _itertools.imap(cond_func, languages)
    return reduce(_operator.or_, conds)


def apply_searchtree_to_query(query, searchtree, languages=None):

    if languages is None:
        languages = get_default_search_languages()
    assert languages
    languages = tuple(languages)

    def walk(n):
        from core import Node
        if isinstance(n, And):
            return walk(n.left) & walk(n.right)

        elif isinstance(n, Or):
            return walk(n.left) | walk(n.right)

        elif isinstance(n, AttributeMatch):
            return _make_attribute_fts_cond(languages, Node.attrs[n.attribute].astext, n.searchterm)

        elif isinstance(n, FulltextMatch):
            return make_fulltext_expr_tsvec(languages, n.searchterm)

        elif isinstance(n, FullMatch):
            fulltext_cond = make_fulltext_expr_tsvec(languages, n.searchterm)
            attrs_cond = _make_attrs_expr_tsvec(languages, n.searchterm)
            return fulltext_cond | attrs_cond

        elif isinstance(n, AttributeCompare):
            return comparisons[n.op](Node.attrs[n.attribute].astext, n.compare_to)

        elif isinstance(n, TypeMatch):
            return Node.type == n.nodetype

        elif isinstance(n, SchemaMatch):
            return Node.schema == n.schema

        else:
            raise NotImplementedError(str(n))

    return query.filter(walk(searchtree))


def _check_search_indexes_node(type, languages):
    """
    checks if search indexes exists and create them if they not exists
    :param type: "attrs" or "fulltext"
    :param languages: tuple of languages
    :return: None
    """

    index_prefix = "ix_{type}_node".format(type=type)
    index_auto_prefix = _utils.make_db_auto_prefix(index_prefix)
    current_indexnames = set()
    res = db.session.execute(
        "SELECT indexname FROM pg_indexes WHERE schemaname = '{schema}' AND tablename = 'node'".format(schema=_DB_SCHEMA_NAME))
    for index in res.fetchall():
        indexname = index[0]
        if indexname.startswith(index_auto_prefix):
            current_indexnames.add(indexname)

    wanted_indexnames = set()
    wanted_indexes_lang = {}
    for lang in languages:
        indexname = _utils.make_db_auto_name(index_prefix, "index", lang)
        wanted_indexnames.add(indexname)
        wanted_indexes_lang[indexname] = lang

    needed_indexnames = wanted_indexnames - current_indexnames
    needed_indexes = []
    for indexname in needed_indexnames:
        lang = wanted_indexes_lang[indexname]
        if type == "attrs":
            indexfunc = func.jsonb_object_values_to_tsvector(lang, Node.attrs)
        else:
            indexfunc = func.to_tsvector_safe(lang, Node.fulltext)
        needed_indexes.append(_Index(indexname, indexfunc, postgresql_using="gin"))
        logg.info('_check_search_indexes_node: create index {}'.format(indexname))

    if needed_indexes:
        map(_operator.methodcaller("create"), needed_indexes)

    for unneeded_index in current_indexnames - wanted_indexnames:
        db.session.execute(
            "DROP INDEX {}".format(unneeded_index))
    db.session.commit()


def check_fulltext_attrs_search_indexes_node():
    """
    checks if search indexes for attributes and fulltext exists and create them if not
    unused indexes are removed
    :return: None
    """
    languages = get_default_search_languages()
    with _locks.named_lock('createsearchindices'):
        _check_search_indexes_node("attrs", languages)
        _check_search_indexes_node("fulltext", languages)
