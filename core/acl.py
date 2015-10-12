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
import core.users as users
import logging
import core.tree as tree
import core.config as config
from utils.log import logException
from core.db import database
from utils.boolparser import BoolParser
import thread
import time
import hashlib

logb = logging.getLogger('backend')

rules = {}
conn = database.getConnection()

aclrule2privilege = {}
aclrule2privilege_length = 0
aclrule2privilege_count = 0
userip2level = {}

acllock = thread.allocate_lock()


class AccessData:

    def __init__(self, req=None, user=None, ip=None):
        if req is not None:
            self.user = users.getUserFromRequest(req)
            self.ip = req.ip or "127.0.0.1"
        else:
            self.user = user
            self.ip = ip or "127.0.0.1"
        self.level = None
        self.allowed_rules = {}

    def getPrivilegeLevel(self):
        return 0  # deactivate priviledge levels for now

        acllock.acquire()
        try:
            global aclrule2privilege_length, aclrule2privilege_count
            key = self.getUserName() + "#" + self.ip
            if key in userip2level:
                return userip2level[key]
            logb.info("Calculating access privilege level for user " + self.getUserName())
            if self.user.isAdmin():
                level = 0
            else:
                string = ""
                acls = sorted(conn.getActiveACLs())
                for clause in acls:
                    if getRule(clause).getParsedRule().has_access(self, tree.getRoot()):
                        string += "1"
                    else:
                        string += "0"
                if len(string) != aclrule2privilege_length:
                    aclrule2privilege.clear()
                    aclrule2privilege_length = len(string)
                    aclrule2privilege_count = 1
                if string in aclrule2privilege:
                    logb.info("(Existing) access string is " + string)
                    level = aclrule2privilege[string]
                else:
                    logb.info("(New) access string is " + string)
                    level = aclrule2privilege_count
                    aclrule2privilege[string] = level
                    aclrule2privilege_count = aclrule2privilege_count + 1
            userip2level[key] = level
            logb.info("Level for user " + self.getUserName() + " is " + str(level))
            return level
        finally:
            acllock.release()

    def getUser(self):
        return self.user

    def getUserName(self):
        return self.user.getName()

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

    def hasAccess(self, node, type, fnode=None):
        if fnode is None:
            fnode = node

        # special cases
        if self.user.isAdmin():
            return 1
        if node.type == "root" and type == "read":
            return 1

        rights = node.getAccess(type)
        if rights:
            if self._checkRights(rights, fnode):
                return 1
            else:
                if type != "write":
                    return 0
        for p in node.getParents():
            if self.hasAccess(p, type, fnode):
                return 1
        return 0

    def hasReadAccess(self, node, fnode=None):
        return self.hasAccess(node, "read", fnode)

    def hasWriteAccess(self, node, fnode=None):

        # check for explicit restriction with "NOT" rule
        try:
            rule = getRule(node.getAccess("write")).getRuleStr() + " "
        except:
            rule = ""
        for n in node.getParents():
            try:
                rule += getRule(n.getAccess("write")).getRuleStr() + " "
            except:
                continue
        if self.user.isAdmin():  # administrator
            return 1
        if rule.find("NOT ( true )") > 0:  # nobody rule found
            return 0
        for grp in self.user.getGroups():  # not rule found
            if rule.find("NOT ( group %s )" % grp) > 0:
                return 0

        return self.hasAccess(node, "write", fnode)

    def filter(self, nodelist, accesstype="read"):
        if accesstype != "read":
            return self.filter_old(nodelist, accesstype)
        if self.user.isAdmin():
            return nodelist

        if len(nodelist) and isinstance(nodelist[0], type("")):
            # convert list of ids to list of nodes
            nodelist = tree.NodeList(nodelist)

        t1 = time.time()
        print "filtering..."
        newlist = []
        for node in nodelist:
            l = node.getLocalRead()
            for clause in l.split(","):
                if clause not in self.allowed_rules:
                    rule = getRule(clause)
                    self.allowed_rules[clause] = rule.getParsedRule().has_access(self, node)
                if self.allowed_rules[clause]:
                    newlist += [node.id]
                    break
        t2 = time.time()

        print "done, %.4f seconds" % (t2 - t1)
        return tree.NodeList(newlist)

    def filter_old(self, nodelist, accesstype="read"):
        if self.user.isAdmin():
            return nodelist

        # optimized version of
        # newlist = [];for node in nodelist: if self.hasReadAccess(node): newlist += [node]

        newlist = []
        lastparent = None
        if type == "read":
            lastaccess = self.hasReadAccess(tree.getRoot())
        elif type == "write":
            lastaccess = self.hasWriteAccess(tree.getRoot())

        for node in nodelist:
            newnode = node
            if isinstance(node, type("")):  # id
                try:
                    node = tree.getNode(node)
                except tree.NoSuchNodeError:
                    continue
                newnode = node.id
            #rights = node.getAccess("read")
            rights = node.getAccess(accesstype)
            if rights:
                if not self._checkRights(rights, node):
                    continue
                else:
                    newlist += [newnode]
                    continue
            p = node.getParents()
            if p != lastparent:
                access = 0
                for p in node.getParents():
                    if accesstype == "read" and self.hasReadAccess(p, node):
                        access = 1
                        break
                    elif accesstype == "write" and self.hasWriteAccess(p, node):
                        access = 1
                        break
                lastaccess = access
            else:
                access = lastaccess
            lastparent = p
            if access:
                newlist += [newnode]

        #logb.info("Filtering "+str(len(nodelist))+" nodes for read-access: "+str(len(newlist))+" nodes")
        logb.info("Filtering " + str(len(nodelist)) + " nodes for " + accesstype + "-access: " + str(len(newlist)) + " nodes")
        return newlist

    def verify_request_signature(self, req_path, params):
        # we generate the signature from the shared secret, the request path and all sorted parameters
        # as described in the upload api documentation
        _p = params.copy()

        if 'user' not in _p and 'sign' not in _p:
            return False

        try:
            workingString = ""
            for n in [h for h in tree.getRoot('home').getChildren() if h.get('system.oauthuser') == params.get('user')]:
                workingString = n.get('system.oauthkey')
                break
        except:
            return False

        workingString += req_path

        # remove signature form parameters before we calculate the test signature
        signature = _p['sign']
        del _p['sign']

        keylist = sorted(_p.keys())

        isFirst = True

        for oneKey in keylist:
            oneValue = _p[oneKey]
            if not isFirst:
                workingString += '&'
            else:
                isFirst = False
            workingString += '{}={}'.format(oneKey,
                                            oneValue)
        testSignature = hashlib.md5(workingString).hexdigest()
        return (testSignature == signature)


def getRootAccess():
    return AccessData(user=users.getUser(config.get('user.adminuser', 'Administrator')))

prefix2conditionclass = {}


class ACLParseException:

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "parse exception: " + self.msg + "\n"


class AccessCondition:

    def __init__(self):
        pass

    def __str__(self):
        return "<undefined>"

    def has_access(self, accessdata, node):
        return 1

""" Function for plugging in foreign checks """


def registerRule(prefix, pclass):
    prefix2conditionclass[prefix] = pclass


class AccessRule:

    def __init__(self, name, rulestr=None, description=None):
        self.name = name
        self.rulestr = rulestr
        if rulestr != "":
            self.parsedRule = parse(rulestr)
        else:
            self.parsedRule = ""
        self.description = description

    def getName(self):
        return self.name

    def setName(self, newname):
        self.name = newname

    def getRuleStr(self):
        return self.rulestr

    def setRuleStr(self, newrule):
        self.rulestr = newrule

    def getDescription(self):
        return self.description

    def setDescription(self, newdesc):
        self.description = newdesc

    def setParsedRule(self, str):
        self.parsedRule = parse(str)

    def getParsedRule(self):
        return self.parsedRule

    def ruleUsage(self):
        return conn.ruleUsage(self.name)


class ACLAndCondition(AccessCondition):

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + str(self.a) + ") AND (" + str(self.b) + ")"

    def has_access(self, accessdata, node):
        return self.a.has_access(accessdata, node) and self.b.has_access(accessdata, node)


class ACLOrCondition(AccessCondition):

    def __init__(self, a, b):
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
        return "user " + self.name

    def has_access(self, accessdata, node):
        if accessdata.user.getName() == self.name:
            return 1
        return 0


class ACLGroupCondition(AccessCondition):

    def __init__(self, group):
        self.group = group

    def __str__(self):
        return "group " + self.group

    def has_access(self, accessdata, node):
        for group in accessdata.user.getGroups():
            if group == self.group:
                return 1
        return 0


class ACLIPCondition(AccessCondition):

    def __init__(self, ip):
        if '/' in ip:
            self.ip = ip[0:ip.index('/')]
            self.netmask = int(ip[ip.index('/') + 1:])
        else:
            self.ip = ip
            self.netmask = 32
        b = self.ip.split(".")
        self.hex = (int(b[0]) << 24) | (int(b[1]) << 16) | (int(b[2]) << 8) | (int(b[3]) << 0)

    def __str__(self):
        return "ip " + self.ip + "/" + str(self.netmask)

    def has_access(self, accessdata, node):
        try:
            b = accessdata.ip.split(".")
            hex = (int(b[0]) << 24) | (int(b[1]) << 16) | (int(b[2]) << 8) | (int(b[3]) << 0)
        except:
            return 0
        if (self.hex ^ hex) & (0xffffffff << (32 - self.netmask)):
            return 0
        else:
            return 1


class ACLDateAfterClause(AccessCondition):

    def __init__(self, date, end):
        self.end = end
        self.date = date

    def __str__(self):
        if self.end:
            return "date > " + self.date
        else:
            return "date >= " + self.date

    def has_access(self, accessdata, node):
        from utils.date import now, parse_date
        return int(now().int() >= parse_date(self.date, "dd.mm.yyyy").int())


class ACLDateBeforeClause(AccessCondition):

    def __init__(self, date, end):
        self.end = end
        self.date = date

    def __str__(self):
        if self.end:
            return "date <= " + self.date
        else:
            return "date < " + self.date

    def has_access(self, accessdata, node):
        from utils.date import now, parse_date
        return int(now().int() <= parse_date(self.date, "dd.mm.yyyy").int())


class ACLParser(BoolParser):

    def parseSimpleCondition(self, s):
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
            s = s[5:].strip()
            if s.startswith(">="):
                return ACLDateAfterClause(s[2:].strip(), 0)
            elif s.startswith("<="):
                return ACLDateBeforeClause(s[2:].strip(), 1)
            elif s.startswith(">"):
                return ACLDateAfterClause(s[1:].strip(), 1)
            elif s.startswith("<"):
                return ACLDateBeforeClause(s[1:].strip(), 0)

        for prefix, pclass in prefix2conditionclass.items():
            if s2.startswith(prefix):
                return pclass(s2)
        raise ACLParseException("syntax error: " + s)

    def default(self):
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


def getRule(name):
    try:
        return rules[name]
    except KeyError:
        # implicit rule?
        if name.startswith("{") and name.endswith("}"):
            r = name[1:-1]
            description, text = r, r
        else:
            try:
                description, text = conn.getRule(name)
            except:  # return false
                description = "( not true )"
                text = "dummy_rule"

        rule = AccessRule(name, description, text)
        rulestr = rule.getRuleStr()

        if rulestr:
            parsedrule = rulestr
        else:
            parsedrule = trueCondition

        rule.setParsedRule(parsedrule)

        rules[name] = rule
        return rule


def getRuleList():
    rlist = []
    dbrules = conn.getRuleList()

    for rule in dbrules:
        rlist += [AccessRule(rule[0], rule[2], rule[1], )]
    return rlist


def updateRule_old(rule, oldrule="", newname="", oldname=""):
    conn.updateRule(rule)
    rules[rule.getName()] = rule
    flush()


def updateRule(rule, oldrule="", newname="", oldname=""):
    """ rule is the new rule
        oldrule is the name of the old and previous rule"""
    if oldrule == "":
        oldrule = rule
    else:
        oldrule = getRule(oldrule)

    conn.updateRule(rule, oldrule.getName())
    rules[oldrule.getName()] = rule
    rules[rule.getName()] = rule

    if (oldrule.getName() != rule.getName()):
        for n in tree.getRoot().getAllChildren():
            n.overwriteAccess(rule, oldrule)

    if (newname != oldname and newname != ""):
        tempoldname = " " + oldname + " "
        tempnewname = " " + newname + " "
        for aclrule in getRuleList():
            if (tempoldname in aclrule.getRuleStr()):
                newrulestr = aclrule.getRuleStr().replace(tempoldname, tempnewname)
                newrule = AccessRule(aclrule.getName(), newrulestr, aclrule.getDescription())
                conn.updateRule(newrule, newrule.getName())
                rules[aclrule.getName()] = newrule


def addRule(rule):
    conn.addRule(rule)
    flush()


def existRule(rulename):
    try:
        description, text = conn.getRule(str(rulename))
        if text != "":
            return True
    except:
        return False


def deleteRule(rulename):
    conn.resetNodeRule(rulename)
    conn.deleteRule(rulename)
    try:
        rules.pop(rulename)
    except:
        None
    flush()


# returns a list of all not defined rulenames used in nodes
def getMissingRuleNames():
    ret = []
    for rule in conn.getAllDBRuleNames():  # saved rulenames in nodes
        if not existRule(rule) and not rule.startswith("{"):
            ret.append(rule)
    return ret


def resetNodeRule(rulename):
    conn.resetNodeRule(rulename)


def getDefaultGuestAccessRule():
    name = config.get("config.default_guest_access_name", "").strip()
    if not name:
        raise BaseException("no default guest name definded in configuration file")
    return AccessRule(name, rulestr="(true)")


def flush():
    global aclrule2privilege_length, aclrule2privilege_count
    rules.clear()
    aclrule2privilege.clear()
    userip2level.clear()
    aclrule2privilege_length = 0
    aclrule2privilege_count = 0


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
    # print str(parse("(user author1A ) or  ( ((group editorgroup1) or (group editorgroup2)))"))
    print str(p.parse("ip 131.159.16.0/24"))
    print str(p.parse("ip 131.159.16.10"))

    class Access:
        pass
    a = Access()
    a.ip = "131.159.16.12"
    assert p.parse("ip 131.159.16.12").has_access(a, None)
    assert not p.parse("ip 131.159.16.11").has_access(a, None)
    assert p.parse("ip 131.159.16.0/24").has_access(a, None)
    assert not p.parse("ip 131.159.17.0/24").has_access(a, None)
    assert p.parse("ip 131.159.16.10 or ip 131.159.16.11 or ip 131.159.16.12 or ip 131.159.16.13 or ip 131.159.16.14").has_access(a, None)


def makeList(req, name, rights, readonlyrights, overload=0, type=""):
    rightsmap = {}
    rorightsmap = {}
    for r in rights:
        rightsmap[r] = None

    rulelist = acl.getRuleList()

    val_left = ""
    val_right = ""

    if not (len(rightsmap) > 0 and overload):
        # inherited standard rules
        for rule in rulelist:
            if rule.getName() in readonlyrights:
                val_left += """<optgroup label="%s"></optgroup>""" % (rule.getDescription())
                rorightsmap[rule.getName()] = 1

        # inherited implicit rules
        for rule in readonlyrights:
            if rule not in rorightsmap:
                val_left += """<optgroup label="%s"></optgroup>""" % (rule)

    # node-level standard rules
    for rule in rulelist:
        if rule.getName() in rightsmap:
            val_left += """<option value="%s">%s</option>""" % (rule.getName(), rule.getDescription())
            rightsmap[rule.getName()] = 1

    # node-level implicit rules
    for r in rightsmap.keys():
        if not rightsmap[r] and r not in rorightsmap:
            val_left += """<option value="%s">%s</option>""" % (r, r)

    for rule in rulelist:
        if rule.getName() not in rightsmap and rule.getName() not in rorightsmap:
            val_right += """<option value="%s">%s</option>""" % (rule.getName(), rule.getDescription())

    return {"name": name, "val_left": val_left, "val_right": val_right, "type": type}
