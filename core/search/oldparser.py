#!/usr/bin/python
"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>


XXX: Old search parser, this is only used for the (soon-to-be legacy) export webservice.
XXX: Will be deleted someday...
"""

import re
from utils.utils import u, intersection, union
from utils.boolparser import BoolParser

pattern_op = re.compile('^([a-zA-Z0-9._-]+)\s*(=|>=|<=|<|>)\s*"?([^"]*)"?$')


class FtsSearchAndCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + str(self.a) + ") AND (" + str(self.b) + ")"

    def execute(self):
        ids1 = self.a.execute()
        if not len(ids1):
            return ids1
        ids2 = self.b.execute()
        return intersection([ids1, ids2])


class FtsSearchOrCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + str(self.a) + ") OR (" + str(self.b) + ")"

    def execute(self):
        ids1 = self.a.execute()
        ids2 = self.b.execute()
        return union([ids1, ids2])


class FtsSearchFieldCondition:

    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value

    def __str__(self):
        return self.field + " " + self.op + " " + self.value

    def execute(self):
        from core.tree import searcher
        return searcher.run_search(self.field, self.op, self.value)


class FtsSearchParser(BoolParser):

    def parseSimpleCondition(self, s):
        m = pattern_op.match(s)
        if m:
            field = m.group(1)
            op = m.group(2)
            value = m.group(3)
            return FtsSearchFieldCondition(field, op, value)
        else:
            return FtsSearchFieldCondition("full", "=", s)

    def default(self):
        return FtsSearchFieldCondition("full", "=", "")

    def getAndClass(self):
        return FtsSearchAndCondition

    def getOrClass(self):
        return FtsSearchOrCondition
