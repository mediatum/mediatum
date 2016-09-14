# -*- coding: utf-8 -*-
"""
    Transform the search language representation into SQLAlchemy query objects.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from sqlalchemy import func, Text, text
from core import config, db
from core.search import SearchQueryException
from core.search.representation import AttributeMatch, FullMatch, SchemaMatch, FulltextMatch, AttributeCompare, TypeMatch, And, Or, Not
from core.database.postgres import mediatumfunc, DeclarativeBase, integer_pk, integer_fk, C, FK
from sqlalchemy.dialects.postgresql.base import TSVECTOR
from core.database.postgres.node import Node
from core.search.config import get_default_search_languages


comparisons = {
    ">": (lambda l, r: l > r),
    "<": (lambda l, r: l < r),
    ">=": (lambda l, r: l >= r),
    "<=": (lambda l, r: l <= r),
    "eq": (lambda l, r: l == r)
}

logg = logging.getLogger(__name__)


class Fts(DeclarativeBase):

    __tablename__ = "fts"

    id = integer_pk()
    # XXX: we allow multiple search items with the same configuration
    # XXX: otherwise, we could use nid, config, searchtype as primary key
    # XXX: may change in the future
    nid = C(FK(Node.id, ondelete="CASCADE"))
    config = C(Text)
    searchtype = C(Text)
    tsvec = C(TSVECTOR)


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


def _escape_postgres_ts_operators(t):
    return (t
            .replace(u'\\', ur'\\')
            .replace(u"&", ur"\&")
            .replace(u"|", ur"\|")
            .replace(u"!", ur"\!")
            .replace(u":", ur"\:")
            .replace(u'"', ur'\"')
            .replace(u'(', ur'\(')
            .replace(u')', ur'\)')
    )


def _prepare_searchstring(op, searchstring):
    searchstring_cleaned = searchstring.strip().strip('"').strip()
    terms = searchstring_cleaned.split()
    # escape chars with special meaning in postgres tsearch
    terms = [_escape_postgres_ts_operators(t) for t in terms]
    # Postgres needs the form term:* for prefix search, we allow simple stars at the end of the word
    terms = [_rewrite_prefix_search(t) if u"*" in t else t for t in terms]
    rewritten_searchstring = op.join(t for t in terms if t)

    if not rewritten_searchstring:
        raise SearchQueryException("invalid query for postgres full text search: " + searchstring)

    return rewritten_searchstring


def make_fts_expr_tsvec(languages, target, searchstring, op="&"):
    """Searches tsvector column. `target` should have a gin index.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type tsvector
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    languages = list(languages)
    prepared_searchstring = _prepare_searchstring(op, searchstring)

    ts_query = func.to_tsquery(languages[0], prepared_searchstring)

    for language in languages[1:]:
        ts_query = ts_query.op("||")(func.to_tsquery(language, prepared_searchstring))

    return target.op("@@")(ts_query)


def make_fts_expr(languages, target, searchstring, op="&"):
    """Searches fulltext column, building ts_vector on the fly.
    `target` must have a gin index built with an ts_vector or this will be extremly slow.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type text
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    languages = list(languages)
    prepared_searchstring = _prepare_searchstring(op, searchstring)
    tsvec = mediatumfunc.to_tsvector_safe(languages[0], target)

    for language in languages[1:]:
        tsvec = tsvec.op("||")(mediatumfunc.to_tsvector_safe(language, target))

    return make_fts_expr_tsvec(languages, tsvec, prepared_searchstring, op)


def make_attribute_fts_cond(languages, target, searchstring, op="&"):
    """Searches fulltext column, building ts_vector on the fly.
    `target` must have a gin index built with an ts_vector or this will be extremly slow.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type text
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    languages = list(languages)
    prepared_searchstring = _prepare_searchstring(op, searchstring)

    def cond_func(lang):
        return mediatumfunc.to_tsvector_safe(lang, func.replace(target, ";", " ")).op("@@")(func.to_tsquery(lang, prepared_searchstring))

    cond = cond_func(languages[0])

    for language in languages[1:]:
        cond |= cond_func(language)

    return cond


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
        languages = get_default_search_languages()

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
            return make_attribute_fts_cond(languages, Node.attrs[n.attribute].astext, n.searchterm), False

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
        query = query.outerjoin(Fts)

    return query.filter(searchcond)
