"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
import sys
from utils.boolparser import BoolParser
from core.search.query import query,numquery
from utils.date import parse_date

class SearchAndCondition:
    def __init__(self, a,b):
        self.a = a
        self.b = b
    def __str__(self):
        return "(" + str(self.a) + ") AND (" + str(self.b) + ")"
    def execute(self):
        ids1 = self.a.execute()
        if not len(ids1):
            return ids1
        ids2 = self.b.execute()
        return ids1.intersect(ids2)

class SearchOrCondition:
    def __init__(self, a,b):
        self.a = a
        self.b = b
    def __str__(self):
        return "(" + str(self.a) + ") OR (" + str(self.b) + ")"
    def execute(self):
        ids1 = self.a.execute()
        ids2 = self.b.execute()
        return ids1.union(ids2)

class SearchNotCondition:
    def __init__(self, a):
        self.a = a
    def __str__(self):
        return "NOT (" + str(self.a) + ")"
    def execute(self):
        raise None # not implemented

class SearchFieldCondition:
    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value
    def __str__(self):
        return self.field+" "+self.op+" "+self.value
    def execute(self, attrs=None):
        if self.op and self.op != "=":
            if self.op == ">=":
                v1 = parse_date(self.value).daynum()
                v2 = 2147483648
            elif self.op == ">":
                v1 = parse_date(self.value).daynum()+1
                v2 = 2147483648
            elif self.op == "<":
                v1 = 0
                v2 = parse_date(self.value).daynum()+1
            elif self.op == "<=":
                v1 = 0
                v2 = parse_date(self.value).daynum()
            return numquery(self.field,v1,v2)
        else:
            return query(self.field,self.value)

pattern_op = re.compile('^([a-zA-Z0-9._-]+)\s*(=|>=|<=|<|>)\s*"?([^"]*)"?$')

class SearchParser(BoolParser):
    def parseSimpleCondition(self,s):
        s2 = s.lower()
        m = pattern_op.match(s)
        if m and m.group(3).find(" ")==-1:
            field = m.group(1)
            op = m.group(2)
            value = m.group(3)
            return SearchFieldCondition(field, op, value)
        else:
            c = None
            for t in s2.split(" "):
                c1 = SearchFieldCondition("full","=",t)
                if not c:
                    c = c1
                else:
                    c = SearchAndCondition(c,c1)
            return c

    def default(self):
        return SearchFieldCondition("full","=","")
    
    def getAndClass(self):
        return SearchAndCondition
    def getOrClass(self):
        return SearchOrCondition
    def getNotClass(self):
        return SearchNotCondition

searchParser = SearchParser()

if __name__ == "__main__":
    p = SearchParser()
    print str(p.parse("((true and false and ((false))))"))
    print str(p.parse("photodate > 1.1.2005 and type=image and full=\"Traktor\""))
    print str(p.parse("Traktor"))
    print str(p.parse("Traktor Haube"))
    print str(p.parse("Traktor Haube Hebel and type=image"))
