"""
old acl parser
"""

from utils.boolparser import BoolParser


class ACLParseException:

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "parse exception: " + self.msg.encode("utf8") + "\n"


class AccessCondition:

    def __init__(self):
        pass

    def __str__(self):
        return "<undefined>"


class ACLAndCondition(AccessCondition):

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") AND (" + ustr(self.b) + ")"


class ACLOrCondition(AccessCondition):

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __str__(self):
        return "(" + ustr(self.a) + ") OR (" + ustr(self.b) + ")"


class ACLNotCondition(AccessCondition):

    def __init__(self, a):
        self.a = a

    def __str__(self):
        return "NOT (" + ustr(self.a) + ")"


class ACLTrueCondition(AccessCondition):

    def __init__(self):
        pass

    def __str__(self):
        return "TRUE"


class ACLFalseCondition(AccessCondition):

    def __init__(self):
        pass

    def __str__(self):
        return "FALSE"


class ACLUserCondition(AccessCondition):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "user " + self.name


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
        return "ip " + self.ip + "/" + ustr(self.netmask)


class ACLDateAfterClause(AccessCondition):

    def __init__(self, date, end):
        self.end = end
        self.date = date

    def __str__(self):
        if self.end:
            return "date > " + self.date
        else:
            return "date >= " + self.date


class ACLDateBeforeClause(AccessCondition):

    def __init__(self, date, end):
        self.end = end
        self.date = date

    def __str__(self):
        if self.end:
            return "date <= " + self.date
        else:
            return "date < " + self.date


class ACLIPListCondition(AccessCondition):

    def __init__(self, listid):
        self.listid = listid

    def __str__(self):
        return "iplist_" + self.listid


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

        if s2.startswith("iplist "):
            return ACLIPListCondition(s[7:].strip())

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

        raise ACLParseException(u"syntax error: " + s)

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
