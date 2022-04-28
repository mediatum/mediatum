# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from warnings import warn
import core.config as config
import flask_login
from core.translation import translate


class UserMixin(object):

    """Provides legacy methods for user objects.
    """

    def getName(self):
        warn("deprecated, use User.display_name or User.login_name instead", DeprecationWarning)
        return self.display_name or self.login_name

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
        raise NotImplementedError("obsolete, use User.can_change_password")

    def setOption(self, o):
        raise NotImplementedError("obsolete, use User.can_change_password")

    def isGuest(self):
        warn("deprecated, use User.is_anonymous instead", DeprecationWarning)
        return self.is_anonymous

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

    def getUserID(self):
        warn("deprecated, use User.id instead", DeprecationWarning)
        return self.id


class GuestUser(UserMixin, flask_login.AnonymousUserMixin):

    """
    A Guest user...
    """
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()

        return cls._instance
    
    @property
    def display_name(self):
        return translate("guest")
    
    def __init__(self):
        self.id = None
        self.is_admin = False
        self.is_editor = False
        self.is_workflow_editor = False
        self.can_change_password = False
        self.login_name = "guest"
        self.group_ids = []
        