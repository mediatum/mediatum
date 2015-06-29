# -*- coding: utf-8 -*-
"""
    Transform the search language representation into SQLAlchemy query objects.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import func as sqlfunc, and_, or_
from core.search.representation import AttributeMatch, FullMatch, SchemaMatch, FulltextMatch, AttributeCompare, TypeMatch, And, Or, Not
from core import Node

comparisons = {
    ">": (lambda l, r: l > r),
    "<": (lambda l, r: l < r),
    ">=": (lambda l, r: l >= r),
    "<=": (lambda l, r: l <= r),
    "=": (lambda l, r: l == r)
}

language = "german"


def make_fulltext_expression_tsvec(language, target, searchterm, op="|"):
    """Searches fulltext column, building ts_vector on the fly.
    `target` must have a gin index built with an ts_vector or this will be extremly slow.
    :param language: postgresql language string
    :param target: SQLAlchemy expression pointing to a text column
    :param searchterm: string of space-separated words to search
    :param op: operator used to join searchterms separated by space, | or &
    """
    tsvec = sqlfunc.to_tsvector(language, target)
    ts_query = sqlfunc.to_tsquery(language, op.join(searchterm.split()))
    return tsvec.op("@@")(ts_query)


def walk(n):
    if isinstance(n, And):
        left = walk(n.left)
        right = walk(n.right)
        return and_(left, right)

    elif isinstance(n, Or):
        left = walk(n.left)
        right = walk(n.right)
        return or_(left, right)

    elif isinstance(n, AttributeMatch):
        return make_fulltext_expression_tsvec(language,
                                              Node.attrs[n.attribute].astext,
                                              n.searchterm)

    elif isinstance(n, FulltextMatch):
        return make_fulltext_expression_tsvec(language, Node.fulltext, n.searchterm)

    elif isinstance(n, FullMatch):
        fulltext_cl = make_fulltext_expression_tsvec(language, Node.fulltext, n.searchterm)
        attrs_cl = make_fulltext_expression_tsvec(language, Node.attrs, n.searchterm)
        return or_(fulltext_cl, attrs_cl)

    elif isinstance(n, AttributeCompare):
        return comparisons[n.op](Node.attrs[n.attribute].astext, n.compare_to)

    elif isinstance(n, TypeMatch):
        return Node.type == n.nodetype

    elif isinstance(n, SchemaMatch):
        return Node.schema == n.schema

    else:
        raise NotImplementedError(str(n))
