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
import core.tree as tree
from utils.utils import u, intersection, union
from utils.boolparser import BoolParser

DEBUG = False
pattern_op = re.compile('^([\:a-zA-Z0-9._-]+)\s*(=|>=|<=|<|>|[Ll][Ii][Kk][Ee])\s*"?([^"]*)"?$')

class OAISearchAndCondition:
    def __init__(self, a,b):
        self.a = a
        self.b = b
    def __str__(self):
        return "(" + str(self.a) + ") AND (" + str(self.b) + ")"
    def execute(self):
        ids = self.a.execute()
        if not len(ids):
            return ids
        return intersection([ids, self.b.execute()])

class OAISearchOrCondition:
    def __init__(self, a,b):
        self.a = a
        self.b = b
    def __str__(self):
        return "(" + str(self.a) + ") OR (" + str(self.b) + ")"
    def execute(self):
        return union([self.a.execute(), self.b.execute()])

class OAISearchFieldCondition:
    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value
    def __str__(self):
        return self.field+" "+self.op+" "+self.value
    def execute(self):
        fieldprefix = 'fts:'
        if self.field.startswith(fieldprefix):
            if DEBUG:
                logging.getLogger('oai').info('OAISearchParser: ---> calling fts:'+ self.field+" "+self.op+" "+self.value)
            from core.tree import searcher
            return searcher.run_search(self.field.replace(fieldprefix, ''), self.op, self.value)

        if self.field=='schema' and self.op=='=':
            sql = "SELECT id FROM node WHERE type LIKE %s"
            params = ("%" + self.value, )
        elif self.field and self.op and self.value:
            sql = "SELECT id FROM node, nodeattribute WHERE id=nid and nodeattribute.name=%s and nodeattribute.value "+ self.op + " %s",
            params = (self.field, self.value)
        else:
            if DEBUG:
                logging.getLogger('oai').error('OAISearchParser: ---> OAISearchParser: Error evaluating FieldCondition')
            return []
        if DEBUG:
            logging.getLogger('oai').info('OAISearchParser: ---> going to execute sql: %s with params %s', sql, params)
        res = tree.db.runQuery(sql, params)
        res = [x[0] for x in res]
        if DEBUG:
            logging.getLogger('oai').info('OAISearchParser: ---> sql returned %d results', len(res))
        return list(set(res))


class OAISearchParser(BoolParser):
    def parseSimpleCondition(self, s):
        m = pattern_op.match(s)
        if m:
            return OAISearchFieldCondition(m.group(1), m.group(2), m.group(3))
        else:
            print 'OAISearchParser: ---> Error: no field specified'

    def getAndClass(self):
        return OAISearchAndCondition
    def getOrClass(self):
        return OAISearchOrCondition
