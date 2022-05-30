# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
    Object representation for the mediaTUM search language.
"""

from __future__ import division
from __future__ import print_function

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
