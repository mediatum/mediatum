# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re
import logging
from utils.boolparser import BoolParser


logg = logging.getLogger(__name__)

DEBUG = False

pattern_op = re.compile('^([a-zA-Z0-9._-]+)\s*(=|>=|<=|<|>|[Ll][Ii][Kk][Ee])\s*"?([^"]*)"?$')


class OAINodeCheckerAndCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") AND (" + ustr(self.b) + ")"

    def execute(self, node):
        res = self.a.execute(node)
        if not res:
            return res
        return res and self.b.execute(node)


class OAINodeCheckerOrCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") OR (" + ustr(self.b) + ")"

    def execute(self, node):
        res = self.a.execute(node)
        if res:
            return res
        return res or self.b.execute(node)


class OAINodeCheckerNotCondition:

    def __init__(self, a):
        self.a = a

    def __str__(self):
        return "NOT (" + ustr(self.b) + ")"

    def execute(self, node):
        return not self.a.execute(node)


class OAINodeCheckerFieldCondition:

    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value

    def __str__(self):
        return self.field + " " + self.op + " " + self.value

    def execute(self, node):
        if self.field == 'schema' and self.op == '=':
            return node.getSchema() == self.value
        elif self.field and self.op and self.value:
            if self.op == "=":
                return node.get(self.field).lower() == self.value.lower()
            elif self.op == "<=":
                return node.get(self.field).lower() <= self.value.lower()
            elif self.op == ">=":
                return node.get(self.field).lower() >= self.value.lower()
            elif self.op == "<":
                return node.get(self.field).lower() < self.value.lower()
            elif self.op == ">":
                return node.get(self.field).lower() > self.value.lower()
            elif self.op.lower() == "like":
                if re.match(self.value.replace("%", ".*").lower(), node.get(self.field).lower()):
                    return True
                return False

        logg.debug('OAINodeChecker ---> : Error evaluating FieldCondition')
        return False


class OAINodeChecker(BoolParser):

    def parseSimpleCondition(self, s):
        m = pattern_op.match(s)
        if m:
            return OAINodeCheckerFieldCondition(m.group(1), m.group(2), m.group(3))
        else:
            logg.debug('OAINodeChecker ---> Error: no field specified')

    def getAndClass(self):
        return OAINodeCheckerAndCondition

    def getOrClass(self):
        return OAINodeCheckerOrCondition

    def getNotClass(self):
        return OAINodeCheckerNotCondition
