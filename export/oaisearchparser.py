# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re
import logging
from utils.utils import intersection, union
from utils.boolparser import BoolParser
from core import Node
from core import db
from core.database.postgres.search import comparisons

q = db.query

pattern_op = re.compile('^([\:a-zA-Z0-9._-]+)\s*(=|>=|<=|<|>|[Ll][Ii][Kk][Ee])\s*"?([^"]*)"?$')

logg = logging.getLogger(__name__)


class OAISearchAndCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") AND (" + ustr(self.b) + ")"

    def execute(self):
        ids = self.a.execute()
        if not len(ids):
            return ids
        return intersection([ids, self.b.execute()])


class OAISearchOrCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") OR (" + ustr(self.b) + ")"

    def execute(self):
        return union([self.a.execute(), self.b.execute()])


class OAISearchFieldCondition:

    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value

    def __str__(self):
        return self.field + " " + self.op + " " + self.value

    def execute(self):
        if self.field.startswith('fts:'):  # compatibility for old fields used in fts searcher
            self.field = self.field[4:]

        if self.field == 'schema' and self.op == '=':
            logg.debug('OAISearchParser: ---> getting nodes with schema %s', self.value)
            nodes = q(Node).filter_by(schema=self.value).all()

        elif self.field and self.op and self.value:
            logg.debug('OAISearchParser: ---> going to make the query: Node.attrs["%s"] %s %s', self.field, self.op, self.value)
            if self.op.lower() == 'like':
                nodes = q(Node).filter(Node.a[self.field].like(self.value)).all()
            else:
                nodes = q(Node).filter(comparisons[self.op](Node.attrs[self.field].astext, self.value)).all()
        else:
            logg.debug('OAISearchParser: ---> OAISearchParser: Error evaluating FieldCondition')
            return []
        logg.debug('OAISearchParser: ---> sql returned %d results', len(nodes))
        return list(set(nodes))


class OAISearchParser(BoolParser):

    def parseSimpleCondition(self, s):
        m = pattern_op.match(s)
        if m:
            return OAISearchFieldCondition(m.group(1), m.group(2), m.group(3))
        else:
            logg.debug('OAISearchParser: ---> Error: no field specified')

    def getAndClass(self):
        return OAISearchAndCondition

    def getOrClass(self):
        return OAISearchOrCondition
