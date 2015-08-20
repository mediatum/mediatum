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
import logging
from warnings import warn
import core.config as config


logg = logging.getLogger(__name__)


class AccessData:

    def __init__(self, req=None, user=None, ip=None):
        warn("core.acl.AccessData is obsolete!")
        from core import users
        if req is not None:
            self.user = users.getUserFromRequest(req)
            self.ip = req.ip or "127.0.0.1"
        else:
            self.user = user
            self.ip = ip or "127.0.0.1"
        self.level = None
        self.allowed_rules = {}

    def hasAccess(self, node, type, fnode=None):
        warn("core.acl disabled, use new access methods on Node / MtQuery!")
        return 1

    def hasReadAccess(self, node, fnode=None):
        return self.hasAccess(node, "read", fnode)

    def hasWriteAccess(self, node, fnode=None):
        warn("core.acl disabled, use new access methods on Node / MtQuery!")
        return 1

    def filter(self, nodelist, accesstype="read"):
        warn("core.acl disabled, use new access methods on Node / MtQuery!")
        return nodelist

    def filter_old(self, nodelist, accesstype="read"):
        warn("core.acl disabled, use new access methods on Node / MtQuery!")
        return nodelist

    def verify_request_signature(self, req_path, params):
        warn("core.acl disabled")
        return True


def getRootAccess():
    from core import users
    # XXX: ACL check disabled, new ACL system later ;)
    warn("core.acl.getRootAccess must not be used anymore")
    return AccessData(user=users.getUser(config.get('user.adminuser', 'Administrator')))


def registerRule(prefix, pclass):
    raise Exception("core.acl disabled")


def parse(r):
    raise Exception("core.acl disabled")


def getRule(name):
    raise Exception("core.acl disabled")


def getRuleList():
    raise Exception("core.acl disabled")


def updateRule_old(rule, oldrule="", newname="", oldname=""):
    raise Exception("core.acl disabled")


def updateRule(rule, oldrule="", newname="", oldname=""):
    raise Exception("core.acl disabled")


def addRule(rule):
    raise Exception("core.acl disabled")


def existRule(rulename):
    raise Exception("core.acl disabled")


def deleteRule(rulename):
    raise Exception("core.acl disabled")


def getMissingRuleNames():
    raise Exception("core.acl disabled")


def resetNodeRule(rulename):
    raise Exception("core.acl disabled")


def getDefaultGuestAccessRule():
    raise Exception("core.acl disabled")


def flush():
    raise Exception("core.acl disabled")
