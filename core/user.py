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
import md5
import core.tree as tree
import core.usergroups as usergroups
import core.config as config
import core.translation as translation

from core.users import useroption

class User(tree.Node):

    def getName(self):
        return self.get("name")
    def setName(self, n):
        return self.set("name", n)
    
    def getGroups(self):
        groups = []
        for p in self.getParents():
            if p.type == "usergroup":
                groups += [p.getName()]
        return groups
        
    def getLastName(self):
        return self.get("lastname")
    def setLastName(self, value):
        self.set("lastname", value)
 
    def getFirstName(self):
        return self.get("firstname")
    def setFirstName(self, value):
        self.set("firstname", value)
        
    def getTelephone(self):
        return self.get("telephone")
    def setTelephone(self, value):
        self.set("telephone", value)
        
    def getComment(self):
        return self.get("comment")
    def setComment(self, value):
        self.set("comment", value)
 
    def getEmail(self):
        return self.get("email")
    def setEmail(self, m):
        return self.set("email", m)

    def getPassword(self):
        return self.get("password")
    def setPassword(self, p):
        self.set("password", md5.md5(p).hexdigest());

    def inGroup(self, id):
        for group in self.getGroups():
            if group == id:
                return True
        return False

    def getOption(self):
        return self.get("opts")
    def setOption(self, o):
        return self.set("opts", o)        

    def getOptionList(self):
        global useroption
        retList = {}
        myoptions = self.getOption()
        for option in useroption:
            if option.value in myoptions and option.value!="":
                retList[option.getName()] = True
            else:
                retList[option.getName()] = False
        return retList

    def isGuest(self):
        return self.getName() == config.get("user.guestuser")

    def isAdmin(self):
        return self.inGroup(config.get("user.admingroup", "Administration"))

    def isEditor(self):
        for group in self.getGroups():
            if "e" in str(usergroups.getGroup(group).getOption()):
                return True
        return False

    def isWorkflowEditor(self):
        for group in self.getGroups():
            if "w" in str(usergroups.getGroup(group).getOption()):
                return True
        return False

    def stdPassword(self):
        return self.get("password") == md5.md5(config.get("user.passwd")).hexdigest()

    def resetPassword(self, newPwd):
        self.set("password", md5.md5(newPwd).hexdigest());

    def translate(self,key):
        return translation.translate(key=key,user=self)

    def isContainer(node):
        return 0
        
    def setUserType(self, value):
        self.usertype = value
    def getUserType(self):
        try:
            return self.usertype
        except AttributeError:
            return ""

    def setOrganisation(self, value):
        self.set("organisation", value)
    def getOrganisation(self):
        return self.get("organisation")
            
    def allowAdd(self):
        return 1
  
class ExternalUser:

    def getUserType(self):
        return self.usertype
        
    def getUser(self):
        raise "not implemented"

    def authenticate_login(self, username, password):
        raise "notImplemented"
        
    def getName(self):
        return ""
        
    def allowAdd(self):
        return 0