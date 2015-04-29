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
from warnings import warn
import core.config as config


class UserMixin(object):

    """Provides legacy methods for user objects.
    """

    def getName(self):
        warn("deprecated, use User.display_name or User.login_name instead", DeprecationWarning)
        return self.display_name

    def getGroups(self):
        warn("deprecated, use User.groups instead", DeprecationWarning)
        return self.groups

    def getLastName(self):
        warn("deprecated, use User.lastname instead", DeprecationWarning)
        return self.lastname

    def setLastName(self, value):
        warn("deprecated, use User.lastname instead", DeprecationWarning)
        self.lastname = value

    def getFirstName(self):
        warn("deprecated, use User.firstname instead", DeprecationWarning)
        return self.firstname

    def setFirstName(self, value):
        warn("deprecated, use User.firstname instead", DeprecationWarning)
        self.firstname = value

    def getTelephone(self):
        warn("deprecated, use User.telephone instead", DeprecationWarning)
        return self.telephone

    def setTelephone(self, value):
        warn("deprecated, use User.telephone instead", DeprecationWarning)
        self.telephone = value

    def getComment(self):
        warn("deprecated, use User.comment instead", DeprecationWarning)
        return self.comment

    def setComment(self, value):
        warn("deprecated, use User.comment instead", DeprecationWarning)
        self.comment = value

    def getEmail(self):
        warn("deprecated, use User.email instead", DeprecationWarning)
        return self.email

    def setEmail(self, m):
        warn("deprecated, use User.email instead", DeprecationWarning)
        self.email = m

    def getPassword(self):
        raise NotImplementedError("does not work anymore!")

    def setPassword(self, p):
        warn("deprecated, use User.password instead", DeprecationWarning)
        raise NotImplementedError("does not work anymore!")

    def inGroup(self, id):
        warn("deprecated, use User.groups instead", DeprecationWarning)
        return id in self.group_ids

    def getOption(self):
        raise NotImplementedError("obsolete, use User.can_change_password or User.can_edit_shoppingbag instead")

    def setOption(self, o):
        raise NotImplementedError("obsolete, use User.can_change_password or User.can_edit_shoppingbag instead")

    def isGuest(self):
        return self.name == config.get("user.guestecser")

    def isAdmin(self):
        warn("deprecated, use User.is_admin instead", DeprecationWarning)
        return self.is_admin

    def isEditor(self):
        warn("deprecated, use User.is_editor instead", DeprecationWarning)
        return self.is_editor

    def isWorkflowEditor(self):
        warn("deprecated, use User.is_workflow_editor instead", DeprecationWarning)
        return self.is_workflow_editor

    def stdPassword(self):
        raise NotImplementedError("no standard passwords!")

    def resetPassword(self, newPwd):
        warn("deprecated, use User.password instead", DeprecationWarning)

    def setUserType(self, value):
        raise NotImplementedError("obsolete, use User.authenticator")

    def getUserType(self):
        raise NotImplementedError("obsolete, use User.authenticator")

    def setOrganisation(self, value):
        warn("deprecated, use User.organisation instead", DeprecationWarning)
        self.set("organisation", value)

    def getOrganisation(self):
        warn("deprecated, use User.organisation instead", DeprecationWarning)
        return self.organisation

    def canChangePWD(self):
        raise NotImplementedError("later!")
        if self.isAdmin():
            return 0
        if self.getUserType() == "users":
            return "c" in self.getOption()
        else:
            from core.users import authenticators
            return authenticators[self.getUserType()].canChangePWD()

    def getShoppingBag(self, name=u""):
        raise NotImplementedError("later!")
        warn("deprecated, use User.shoppingbags instead", DeprecationWarning)
        ret = []
        for c in self.getChildren():
            if c.getContentType() == "shoppingbag":
                if unicode(c.id) == name or c.getName() == name:
                    return [c]
                else:
                    ret.append(c)
        return ret

    def addShoppingBag(self, name, items=[]):
        raise NotImplementedError("later!")
        sb = Node(name, type="shoppingbag")
        sb.setItems(items)
        self.addChild(sb)

    def getUserID(self):
        warn("deprecated, use User.id instead", DeprecationWarning)
        return self.id


class ExternalAuth(object):

    def getUserType(self):
        return self.usertype

    def getUser(self):
        raise "not implemented"

    def authenticate_login(self, username, password):
        raise "notImplemented"

    def getName(self):
        return ""

    def canChangePWD(self):
        raise "not implemented"

