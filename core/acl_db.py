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

from db import database
from acl import AccessRule,AccessCondition,prefix2conditionclass,ACLParseException
from parsers.boolean import BoolParser

class ACLAndCondition(AccessCondition):
    def __init__(self, a,b):
        self.a = a
        self.b = b
    def __str__(self):
        return "(" + str(self.a) + ") AND (" + str(self.b) + ")"
    def has_access(self, accessdata, node):
        return self.a.has_access(accessdata, node) and self.b.has_access(accessdata, node)

class ACLOrCondition(AccessCondition):
    def __init__(self, a,b):
        self.a = a
        self.b = b
    def __str__(self):
        return "(" + str(self.a) + ") OR (" + str(self.b) + ")"
    def has_access(self, accessdata, node):
        return self.a.has_access(accessdata, node) or self.b.has_access(accessdata, node)

class ACLNotCondition(AccessCondition):
    def __init__(self, a):
        self.a = a
    def __str__(self):
        return "NOT (" + str(self.a) + ")"
    def has_access(self, accessdata, node):
        return not self.a.has_access(accessdata, node)

class ACLTrueCondition(AccessCondition):
    def __init__(self):
        pass
    def __str__(self):
        return "TRUE"
    def has_access(self, accessdata, node):
        return 1

trueCondition = ACLTrueCondition()

class ACLFalseCondition(AccessCondition):
    def __init__(self):
        pass
    def __str__(self):
        return "FALSE"
    def has_access(self, accessdata, node):
        return 0

class ACLUserCondition(AccessCondition):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return "user "+self.name
    def has_access(self, accessdata, node):
        if accessdata.user.getName() == self.name:
            return 1
        return 0

class ACLGroupCondition(AccessCondition):
    def __init__(self, group):
        self.group = group 
    def __str__(self):
        return "group "+self.group
    def has_access(self, accessdata, node):
        for group in accessdata.user.getGroups():
            if group == self.group:
                return 1
        return 0

class ACLIPCondition(AccessCondition):
    def __init__(self, ip):
        if '/' in ip:
            self.ip = ip[0:ip.index('/')]
            self.netmask = int(ip[ip.index('/')+1:])
        else:
            self.ip = ip 
            self.netmask = 32
        b = self.ip.split(".")
        self.hex = (int(b[0])<<24)|(int(b[1])<<16)|(int(b[2])<<8)|(int(b[3])<<0)
    def __str__(self):
        return "ip "+self.ip+"/"+str(self.netmask)
    def has_access(self, accessdata, node):
        try:
            b = accessdata.ip.split(".")
            hex = (int(b[0])<<24)|(int(b[1])<<16)|(int(b[2])<<8)|(int(b[3])<<0)
        except:
            return 0
        if (self.hex^hex)&(0xffffffff << (32-self.netmask)):
            return 0
        else:
            return 1

class ACLDateAfterClause(AccessCondition):
    def __init__(self, date, end):
        self.end=end
        self.date=date
    def __str__(self):
        if self.end:
            return "date > "+self.date
        else:
            return "date >= "+self.date

class ACLDateBeforeClause(AccessCondition):
    def __init__(self, date, end):
        self.end=end
        self.date=date
    def __str__(self):
        if self.end:
            return "date <= "+self.date
        else:
            return "date < "+self.date

class ACLParser(BoolParser):
    def parseSimpleCondition(self,s):
        s2 = s.lower()
        if s2 == "false":
            return ACLFalseCondition()
        if s2 == "true":
            return ACLTrueCondition()

        if s2.startswith("group "):
            return ACLGroupCondition(s[6:].strip())

        if s2.startswith("user "):
            return ACLUserCondition(s[5:].strip())

        if s2.startswith("ip "):
            return ACLIPCondition(s[3:].strip())

        if s2.startswith("date "):
            s = s[5:].strip();
            if s.startswith(">="):
                return ACLDateAfterClause(s[2:].strip(), 0);
            elif s.startswith("<="):
                return ACLDateBeforeClause(s[2:].strip(), 1);
            elif s.startswith(">"):
                return ACLDateAfterClause(s[1:].strip(), 1);
            elif s.startswith("<"):
                return ACLDateBeforeClause(s[1:].strip(), 0);

        for prefix,pclass in prefix2conditionclass.items():
            if s2.startswith(prefix):
                return pclass(s2)
        print s
        raise ACLParseException("syntax error: " + s);

    def default():
        return ACLTrueCondition()
    
    def getAndClass(self):
        return ACLAndCondition
    def getOrClass(self):
        return ACLOrCondition
    def getNotClass(self):
        return ACLNotCondition

p = ACLParser()

def parse(r):
    return p.parse(r)

conn = None
rules = {}

def getRule(name):
    global rules
    try:
        return rules[name]
    except KeyError:
        # implicit rule?
        if name.startswith("{") and name.endswith("}"):
            r = name[1:-1]
            description,text = r,r
        else:
            description,text = conn.getRule(name)

        rule = AccessRule(name,description,text)
        rulestr = rule.getRuleStr()
        
        if rulestr:
            parsedrule = rulestr
        else:
            parsedrule = trueCondition

        rule.setParsedRule(parsedrule)

        rules[name] = rule
        return rule

def getRuleList():
    global conn
    rlist = []
    dbrules = conn.getRuleList()
    for rule in dbrules:
        rlist += [AccessRule(str(rule[0]), str(rule[2]), str(rule[1]))]
    return rlist

def updateRule(rule):
    global conn, rules
    conn.updateRule(rule)
    rules[rule.getName()] = rule

def addRule(rule):
    global conn
    conn.addRule(rule)

def existRule(rulename):
    global conn
    try:
        description,text = conn.getRule(str(rulename))
        if text!="":
            return True
    except:
        return False


def deleteRule(rulename):
    global conn, rules
    conn.deleteRule(rulename)
    try:
        rules.pop(rulename)
    except:
        None

def flush():
    global rules
    rules.clear()

def initialize():
    global conn
    conn = database.getConnection()

if __name__ == "__main__":
    print str(p.parse("not true or not false"))
    print str(p.parse("true and (true and (true and (true)))"))
    print str(p.parse("((((true) and false) and true) and false) and true"))
    print str(p.parse("true or (true or (true or (true)))"))
    print str(p.parse("((((true) or false) or (true or false)) or (false or true)) or true"))
    print str(p.parse("user admin or user wichtig"))
    print str(p.parse("group wichtigtuer and not group neulinge"))
    print str(p.parse("date >= 01.01.2005"))
    print str(p.parse("date > 01.01.2005"))
    print str(p.parse("date < 01.01.2005"))
    print str(p.parse("date <= 01.01.2005"))
    print str(p.parse("((true and false and ((false))))"))
    #print str(parse("(user author1A ) or  ( ((group editorgroup1) or (group editorgroup2)))"))
    print str(p.parse("ip 131.159.16.0/24"))
    print str(p.parse("ip 131.159.16.10"))

    class Access:
        pass
    a = Access()
    a.ip = "131.159.16.12"
    assert p.parse("ip 131.159.16.12").has_access(a,None)
    assert not p.parse("ip 131.159.16.11").has_access(a,None)
    assert p.parse("ip 131.159.16.0/24").has_access(a,None)
    assert not p.parse("ip 131.159.17.0/24").has_access(a,None)
    assert p.parse("ip 131.159.16.10 or ip 131.159.16.11 or ip 131.159.16.12 or ip 131.159.16.13 or ip 131.159.16.14").has_access(a,None)
