"""
 mediatum - a multimedia content repository

 Copyright (C) 2012 Arne Seifert <arne.seifert@tum.de>


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

from .boolparser import BoolParser
from .utils import union, intersection, isNumeric


class ListParseException:

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "parse exception: " + self.msg + "\n"


class ListCondition():

    def __init__(self):
        pass

    def __str__(self):
        return "<undefined>"

    def getList(self, list):
        return []

    def getHTML(self, andStr, orStr):
        return '()'


class ListTrueCondition(ListCondition):

    def __init__(self):
        pass

    def __str__(self):
        return "TRUE"

    def getList(self, list):
        return [ustr(x) for x in range(0, len(list))][:-1]

    def getHTML(self, andStr, orStr):
        return "True"


class ListFalseCondition(ListCondition):

    def __init__(self):
        pass

    def __str__(self):
        return "FALSE"

    def getList(self, data):
        return []

    def getHTML(self, andStr, orStr):
        return "False"


class ListFieldCondition(ListCondition):

    def __init__(self, field, value):
        self.field = field.strip()
        self.value = value.strip()

    def __str__(self):
        return self.field + " = " + self.value

    def getList(self, data):
        pos = (data[0]).index(self.field.strip())
        ret = []
        for item in data[1:]:
            if item[pos] == self.value.strip():
                ret.append(item[0])
        return ret

    def getHTML(self, andStr, orStr):
        return '<p>' + self.field + ' = ' + self.value + '</p>'


class ListFieldLikeCondition(ListCondition):

    def __init__(self, field, value):
        self.field = field.strip()
        self.value = value.strip()

    def __str__(self):
        return self.field + " like " + self.value

    def getList(self, data):
        pos = (data[0]).index(self.field.strip())
        ret = []
        if self.value.strip().endswith('*'):
            self.value = self.value.strip()[:-1]
        for item in data[1:]:
            if self.value == item[pos][:len(self.value)]:
                ret.append(item[0])
        return ret

    def getHTML(self, andStr, orStr):
        return '<p>' + self.field + ' like ' + self.value + '</p>'


class ListFieldLowerCondition(ListCondition):

    def __init__(self, field, value):
        self.field = field.strip()
        self.value = value.strip()

    def __str__(self):
        return self.field + " < " + self.value

    def getList(self, data):
        pos = (data[0]).index(self.field)
        ret = []
        for item in data[1:]:
            if isNumeric(item[pos].replace(",", ".")) and isNumeric(self.value.replace(",", ".")):
                if float(item[pos].replace(",", ".")) < float(self.value.replace(",", ".")):

                    ret.append(item[0])
            else:
                if item[pos] < self.value:
                    ret.append(item[0])
        return ret

    def getHTML(self, andStr, orStr):
        return '<p>' + self.field + ' < ' + self.value + '</p>'


class ListFieldGreaterCondition(ListCondition):

    def __init__(self, field, value):
        self.field = field.strip()
        self.value = value.strip()

    def __str__(self):
        return self.field + " > " + self.value

    def getList(self, data):
        pos = (data[0]).index(self.field)
        ret = []
        for item in data[1:]:
            if item[pos] > self.value:
                ret.append(item[0])
        return ret

    def getHTML(self, andStr, orStr):
        return '<p>' + self.field + ' > ' + self.value + '</p>'


class ListFieldMethodCondition(ListCondition):

    def __init__(self, field, value):
        self.field = field.strip()
        value = value.split("|")
        self.value = value[0]
        self.method = value[1]

    def __str__(self):
        return self.field + " = " + self.value + " op:" + self.method

    def getList(self, data):
        pos = (data[0]).index(self.field)
        ret = []
        for item in data[1:]:  # todo: create method
            ret.append(item[0])
        return ret

    def getHTML(self, andStr, orStr):
        return "method"


class ListAndCondition(ListCondition):

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") AND (" + ustr(self.b) + ")"

    def getList(self, data):
        return intersection([self.a.getList(data), self.b.getList(data)])

    def getHTML(self, andStr, orStr):
        return andStr().replace("[VALA]", self.a.getHTML(andStr, orStr)).replace("[VALB]", self.b.getHTML(andStr, orStr))


class ListOrCondition(ListCondition):

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") OR (" + ustr(self.b) + ")"

    def getList(self, data):
        return union((self.a.getList(data), self.b.getList(data)))

    def getHTML(self, andStr, orStr):
        return orStr().replace('[VALA]', self.a.getHTML(andStr, orStr)).replace("[VALB]", self.b.getHTML(andStr, orStr))


class ListNotCondition():

    def __init__(self, a):
        self.a = a

    def __str__(self):
        return "NOT (" + ustr(self.a) + ")"

    def getList(self, data):
        return []

    def getHTML(self, andStr, orStr):
        return "not"


class ListDefaultCondition:

    def __init__(self, s):
        self.s = s

    def getList(self, list):
        return list

    def getHTML(self, andStr, orStr):
        return "default"


class ListParser(BoolParser):

    def parseSimpleCondition(self, s):
        s2 = s  # .lower()
        if s2.lower() == "false":
            return ListFalseCondition()
        if s2.lower() == "true":
            return ListTrueCondition()

        s2 = s2.replace("[", "").replace("]", "")

        if "|" in s2:
            field, value = s2.split("=")
            return ListFieldMethodCondition(field, value)
        if "like" in s2:
            field, value = s2.split("like")
            return ListFieldLikeCondition(field, value)
        if "=" in s2:
            field, value = s2.split("=")
            return ListFieldCondition(field, value)
        if "<" in s2:
            field, value = s2.split("<")
            return ListFieldLowerCondition(field, value)
        if ">" in s2:
            field, value = s2.split(">")
            return ListFieldGreaterCondition(field, value)

        raise ListParseException("syntax error: " + s)

    def default(self):
        return ListTrueCondition()

    def getAndClass(self):
        return ListAndCondition

    def getOrClass(self):
        return ListOrCondition

    def getNotClass(self):
        return ListNotCondition


def getAndHTML_():
    return """<div class="and_block selectedBlock">\n\t[VAL]\n</div>"""


def getOrHTML_():
    return """<div class="or_block">\nor<div class="and_block selectedBlock">\n\t[VAL]\n</div>\n</div>"""


if __name__ == "__main__":
    l = [['_id_', 'codelocation', 'tempmin', 'tempmax'], [0, '100203', '10', '39'], [1, '100203', '14', '19']]
    s = "([codelocation=100203]and[tempmin<13])or(([tempmax<20]))"
    lp = ListParser()
    print s
    print lp.parse(s)
    print lp.parse(s).getList(l)
    print lp.parse(s).getHTML(getAndHTML, getOrHTML)
