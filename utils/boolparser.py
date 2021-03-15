# vim: set fileencoding=utf-8 :
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
from __future__ import division

import re
import sys

pattern_bracket = re.compile("\\([^)(]*\\)")
pattern_string = re.compile('"([^"]*)"')
pattern_and = re.compile("\\b[aA][nN][dD]\\b")
pattern_or = re.compile("\\b[oO][rR]\\b")
pattern_not = re.compile("\\s*\\b[nN][oO][tT]\\b\\s*")
pattern_marker = re.compile("@c<([0-9]*)>c@")
pattern_stringmarker = re.compile("@s<([0-9]*)>s@")
pattern_space = re.compile("[ \t\n\r]")


class ParseException:

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "parse exception: " + self.msg + "\n"


class AndCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") AND (" + ustr(self.b) + ")"


class OrCondition:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") OR (" + ustr(self.b) + ")"


class NotCondition:

    def __init__(self, a):
        self.a = a

    def __str__(self):
        return "NOT (" + ustr(self.a) + ")"


class TrueCondition:

    def __init__(self):
        pass

    def __str__(self):
        return "TRUE"


class FalseCondition:

    def __init__(self):
        pass

    def __str__(self):
        return "FALSE"


class BoolParser:

    def extendClauses(self, s, l):
        scanner = pattern_marker.scanner(s)
        while True:
            match = scanner.search()
            if not match:
                break
            c = match.group()
            clause = l[int(match.group(1))]
            s = s.replace(c, clause)
        return s

    def extendStrings(self, s, l):
        scanner = pattern_stringmarker.scanner(s)
        while True:
            match = scanner.search()
            if not match:
                break
            c = match.group()
            string = l[int(match.group(1))]
            s = s.replace(c, string)
        return s

    def replaceStrings(self, s):
        l = []
        while True:
            m = pattern_string.search(s)
            if m:
                clause = m.group(1)
                s = s[0:m.start()] + "@s<" + ustr(len(l)) + ">s@" + s[m.end():]
                l += [clause]
            else:
                break
        return s, l

    def parse2(self, s, l=None, stringlist=None, onlybrackets=0):
        if l is None:
            l = []
        if stringlist is None:
            s, stringlist = self.replaceStrings(s)

        s = s.strip()

        while True:
            # remove outer brackets ()
            while s[0] == '(' and s[-1] == ')' and ('(' not in s[1:-1]) and (')' not in s[1:-1]):
                s = s[1:-1].strip()

            m = pattern_bracket.search(s)
            if m:
                clause = m.group()
                s = s[0:m.start()] + "@c<" + ustr(len(l)) + ">c@" + s[m.end():]
                l += [self.extendClauses(clause, l)]
            else:
                break

        # handle OR
        m = pattern_or.search(s)
        if m:
            if m.start() <= 0:
                raise ParseException("left side of OR missing while parsing \"" + s + "\"")
            if m.end() >= len(s) - 1:
                raise ParseException("right side of OR missing while parsing \"" + s + "\"")

            left = self.parse2(self.extendClauses(s[0:m.start()], l), l, stringlist)
            right = self.parse2(self.extendClauses(s[m.end():], l), l, stringlist)
            return self.getOrClass()(left, right)

        # handle AND
        m = pattern_and.search(s)

        if m:
            if m.start() <= 0:
                raise ParseException("left side of AND missing while parsing \"" + s + "\"")

            if m.end() >= len(s) - 1:
                raise ParseException("right side of AND missing while parsing \"" + s + "\"")

            left = self.parse2(self.extendClauses(s[0:m.start()], l), l, stringlist)
            right = self.parse2(self.extendClauses(s[m.end():], l), l, stringlist)

            return self.getAndClass()(left, right)

        s = s.strip()

        if s.lower().startswith("not "):
            inverse = self.parse2(self.extendClauses(s[4:], l), l, stringlist)
            return self.getNotClass()(inverse)

        term = self.extendClauses(s, l).strip()
        if '(' in term and not onlybrackets:
            return self.parse2(term, l, stringlist, 1)
        else:
            return self.parseSimpleCondition(self.extendStrings(term, stringlist))

    def parse(self, s):
        s = pattern_space.sub(" ", s).strip()
        if len(s) == 0:
            return self.default()
        return self.parse2(s)

    def parseSimpleCondition(self, s):
        s2 = s.lower()
        if s2 == "false":
            return FalseCondition()
        if s2 == "true":
            return TrueCondition()
        raise ParseException("syntax error: " + s)

    def default(self):
        return TrueCondition()

    def getAndClass(self):
        return AndCondition

    def getOrClass(self):
        return OrCondition

    def getNotClass(self):
        return NotCondition


if __name__ == "__main__":
    b = BoolParser()
    print ustr(b.parse("not true or not false"))
    print ustr(b.parse("true and (true and (true and (true)))"))
    print ustr(b.parse("((((true) and false) and true) and false) and true"))
    print ustr(b.parse("true or (true or (true or (true)))"))
    print ustr(b.parse("((((true) or false) or (true or false)) or (false or true)) or true"))
    print ustr(b.parse("((true and false and ((false))))"))

    class StringCondition:

        def __init__(self, s):
            self.s = s

        def __str__(self):
            return "'" + self.s + "'"

    class StringParser(BoolParser):

        def parseSimpleCondition(self, s):
            s2 = s.lower()
            if s2 == "false":
                return FalseCondition()
            if s2 == "true":
                return TrueCondition()
            return StringCondition(s2)
    bb = StringParser()

    print ustr(bb.parse("""test2=test(test)"""))
    print ustr(bb.parse('(("bla (and) bla" and user "blupp" and (("bli bla blo"))))'))
