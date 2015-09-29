# -*- coding: utf-8 -*-
"""
    Object representation for the mediaTUM search language.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from utils.classmagic import Case


class And(Case):

    def __init__(self, left, right): pass


class Or(Case):

    def __init__(self, left, right): pass


class Not(Case):

    def __init__(self, value): pass


class FullMatch(Case):

    def __init__(self, searchterm): pass


class FulltextMatch(Case):

    def __init__(self, searchterm): pass


class AttributeMatch(Case):

    def __init__(self, attribute, searchterm): pass


class AttributeCompare(Case):

    def __init__(self, attribute, op, compare_to): pass


class TypeMatch(Case):

    def __init__(self, nodetype): pass


class SchemaMatch(Case):

    def __init__(self, schema): pass


class AttributeNameMatch(Case):

    def __init__(self, attribute): pass


class UpdateTimeMatch(Case):

    def __init__(self, op, timestamp): pass
