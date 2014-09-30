"""
 mediatum - a multimedia content repository

 Copyright (C) 2008 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2008 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
import logging
from utils.boolparser import BoolParser

DEBUG = False

pattern_op = re.compile('^([a-zA-Z0-9._-]+)\s*(=|>=|<=|<|>|[Ll][Ii][Kk][Ee])\s*"?([^"]*)"?$')


class OAINodeCheckerAndCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + str(self.a) + ") AND (" + str(self.b) + ")"

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
        return "(" + str(self.a) + ") OR (" + str(self.b) + ")"

    def execute(self, node):
        res = self.a.execute(node)
        if res:
            return res
        return res or self.b.execute(node)


class OAINodeCheckerNotCondition:

    def __init__(self, a):
        self.a = a

    def __str__(self):
        return "NOT (" + str(self.b) + ")"

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

        if DEBUG:
            logging.getLogger('oai').info('OAINodeChecker ---> : Error evaluating FieldCondition')
        return False


class OAINodeChecker(BoolParser):

    def parseSimpleCondition(self, s):
        m = pattern_op.match(s)
        if m:
            return OAINodeCheckerFieldCondition(m.group(1), m.group(2), m.group(3))
        else:
            if DEBUG:
                logging.getLogger('oai').info('OAINodeChecker ---> Error: no field specified')

    def getAndClass(self):
        return OAINodeCheckerAndCondition

    def getOrClass(self):
        return OAINodeCheckerOrCondition

    def getNotClass(self):
        return OAINodeCheckerNotCondition
