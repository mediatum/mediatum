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
import core.users
import core.config
import logging
import core.tree
import sys
from utils.log import logException

logb = logging.getLogger('backend')

class AccessData:
    def __init__(self, req=None, user=None, ip=None):
        if req is not None:
            self.user = users.getUserFromRequest(req)
            self.ip = req.ip or "127.0.0.1"
        else:
            self.user = user
            self.ip = ip or "127.0.0.1"

    def getUser(self):
        return self.user

    def _checkRights(self, rights, fnode):
        # fnode is the node against which certain rules
        # (like e.g. user_has_paid_this_image) are checked.
        # It's not necessarily the node from which the
        # rule originates, though.
        try:
            for clause in rights.split(","):
                clause = clause.strip()
                rule = getRule(clause)
                if rule.getParsedRule().has_access(self, fnode):
                    return 1
            return 0
        except ACLParseException:
            logException("Error while parsing ACL clause")
            # if we can't parse the acl rule, we assume no access
            return 0

    def hasAccess(self,node,type,fnode=None):
        if fnode is None:
            fnode = node
            
        #special cases
        if self.user.isAdmin():
            return 1
        if node.type == "root" and type == "read":
            return 1

        rights = node.getAccess(type)
        if rights:
            if self._checkRights(rights, fnode):
                return 1
            else:
                if type!="write":
                    return 0
        for p in node.getParents():
            if self.hasAccess(p,type,fnode):
                return 1
        return 0

    def hasReadAccess(self,node,fnode=None):
        return self.hasAccess(node,"read",fnode)

    def hasWriteAccess(self,node,fnode=None):
        return self.hasAccess(node,"write",fnode)

    def filter(self,nodelist):
        if self.user.isAdmin():
            return nodelist

        # optimized version of
        # newlist = [];for node in nodelist: if self.hasReadAccess(node): newlist += [node]

        newlist = []
        lastparent = None
        lastaccess = self.hasReadAccess(tree.getRoot())
        for node in nodelist:
            newnode = node
            if type(node) == type(""): # id
                try:
                    node = tree.getNode(node)
                except tree.NoSuchNodeError:
                    continue
                newnode = node.id
            rights = node.getAccess("read")
            if rights:
                if not self._checkRights(rights, node):
                    continue
                else:
                    newlist += [newnode]
                    continue
            p = node.getParents()
            if len(p):
                parent = p[0]
            else:
                parent = None
            if parent != lastparent:
                access=0
                for p in node.getParents():
                    if self.hasReadAccess(p,node):
                        access=1
                        break
                lastaccess = access
            else:
                access = lastaccess
            lastparent = parent
            if access:
                newlist += [newnode]

        logb.info("Filtering "+str(len(nodelist))+" nodes for read-access: "+str(len(newlist))+" nodes")
        return newlist

prefix2conditionclass = {}

class ACLParseException:
    def __init__(self,msg):
        self.msg = msg
    def __str__(self):
        return "parse exception: "+self.msg+"\n"

class AccessCondition:
    def __init__(self):
        pass
    def __str__(self):
        return "<undefined>"
    def has_access(self, accessdata, node):
        return 1

""" Function for plugging in foreign checks """
def registerRule(prefix,pclass):
    prefix2conditionclass[prefix] = pclass

class AccessRule:
    def __init__(self, name, rulestr = None, description = None):
        self.name = name
        self.rulestr = rulestr
        if rulestr !="":
            self.parsedRule = parse(rulestr)
        else:
            self.parsedRule = ""
        self.description = description

    def getName(self):
        return self.name

    def getRuleStr(self):
        return self.rulestr

    def getDescription(self):
        return self.description

    def setParsedRule(self, str):
        self.parsedRule = parse(str)

    def getParsedRule(self):
        return self.parsedRule


def getRule(name):
    raise noimpl

def setImplementation(module):
    global getRule
    global getRuleList
    global parse
    global updateRule
    global addRule
    global existRule
    global deleteRule
    getRule = module.getRule
    getRuleList = module.getRuleList
    parse = module.parse
    updateRule = module.updateRule
    addRule = module.addRule
    existRule = module.existRule
    deleteRule = module.deleteRule
    module.initialize()

def getRuleList():
    raise noimpl

def updateRule(rule):
    raise noimpl

def addRule(rule):
    raise noimpl

def existRule(name):
    raise noimpl

def deleteRule(name):
    raise noimpl


