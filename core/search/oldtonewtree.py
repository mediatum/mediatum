# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.search.representation import FulltextMatch, FullMatch, SchemaMatch, TypeMatch, AttributeMatch, AttributeCompare, And, Or, Not
from core.search.oldparser import FtsSearchAndCondition, FtsSearchOrCondition, FtsSearchFieldCondition
from utils.boolparser import NotCondition


old_to_new_field_mapping = {
    "objtype": TypeMatch,
    "schema": SchemaMatch,
    "full": FullMatch,
    "fulltext": FulltextMatch
}


def old_searchtree_to_new(n):
    if isinstance(n, FtsSearchAndCondition):
        return And(old_searchtree_to_new(n.a), old_searchtree_to_new(n.b))

    elif isinstance(n, FtsSearchOrCondition):
        return Or(old_searchtree_to_new(n.a), old_searchtree_to_new(n.b))

    elif isinstance(n, NotCondition):
        return Not(old_searchtree_to_new(n.a))

    elif isinstance(n, FtsSearchFieldCondition):
        new_cls = old_to_new_field_mapping.get(n.field)

        if new_cls is not None:
            return new_cls(n.value)
        elif n.op == "=":
            return AttributeMatch(n.field, n.value)
        else:
            return AttributeCompare(n.field, n.op, n.value)
