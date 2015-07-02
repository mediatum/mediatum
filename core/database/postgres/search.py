# -*- coding: utf-8 -*-
"""
    Transform the search language representation into SQLAlchemy query objects.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import func as sqlfunc, and_, or_, Text
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

language = "german"


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


def make_fts_expr(language, target, searchstring, op="|"):
    """Searches fulltext column, building ts_vector on the fly.
    `target` must have a gin index built with an ts_vector or this will be extremly slow.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type text
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    tsvec = func.to_tsvector_safe(language, target)
    ts_query = sqlfunc.to_tsquery(language, _prepare_searchstring(op, searchstring))
    return tsvec.op("@@")(ts_query)


def make_fts_expr_tsvec(language, target, searchstring, op="|"):
    """Searches tsvector column. `target` should have a gin index.
    :param language: postgresql language string
    :param target: SQLAlchemy expression with type tsvector
    :param searchstring: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    ts_query = sqlfunc.to_tsquery(language, _prepare_searchstring(op, searchstring))
    return target.op("@@")(ts_query)


def apply_searchtree_to_query(query, searchtree):

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
            return make_fts_expr(language,
                                 Node.attrs[n.attribute].astext,
                                 n.searchterm), True

        elif isinstance(n, FulltextMatch):
            cond = (make_fts_expr_tsvec(language, Fts.tsvec, n.searchterm)
                    & (Fts.config == language)
                    & (Fts.searchtype == 'fulltext'))

            return cond, True

        elif isinstance(n, FullMatch):
            cond = (make_fts_expr_tsvec(language, Fts.tsvec, n.searchterm)
                    & (Fts.config == language)
                    & ((Fts.searchtype == 'fulltext') | (Fts.searchtype == 'attrs')))
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
