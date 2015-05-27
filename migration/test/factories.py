# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import string

from factory import fuzzy
from core.test.factories import SQLAFactory, NodeFactory
from migration import import_datamodel
from migration.import_datamodel import Access


class AccessFactory(SQLAFactory):

    class Meta:
        model = Access

    name = fuzzy.FuzzyText(length=6, chars=string.lowercase)
    description = fuzzy.FuzzyText(length=12, chars=string.lowercase)


class ImportNodeFactory(NodeFactory):

    class Meta:
        model = import_datamodel.Node

    type = "directory"
