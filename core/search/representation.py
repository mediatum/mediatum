# -*- coding: utf-8 -*-
"""
    Object representation for the mediaTUM search language.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from utils.classmagic import Case


class SearchTreeElement(Case):
    pass


class And(SearchTreeElement):

    def __init__(self, left, right): pass


class Or(SearchTreeElement):

    def __init__(self, left, right): pass


class Not(SearchTreeElement):

    def __init__(self, value): pass


class FullMatch(SearchTreeElement):

    def __init__(self, searchterm): pass


class FulltextMatch(SearchTreeElement):

    def __init__(self, searchterm): pass


class AttributeMatch(SearchTreeElement):

    def __init__(self, attribute, searchterm): pass


class AttributeCompare(SearchTreeElement):

    def __init__(self, attribute, op, compare_to): pass


class TypeMatch(SearchTreeElement):

    def __init__(self, nodetype): pass


class SchemaMatch(SearchTreeElement):

    def __init__(self, schema): pass


class AttributeNameMatch(SearchTreeElement):

    def __init__(self, attribute): pass


class UpdateTimeMatch(SearchTreeElement):

    def __init__(self, op, timestamp): pass
