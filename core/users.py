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

import core.config as config
import usergroups
import md5
import core.tree as tree
import core.translation
import random
import thread

from utils.utils import Option

useroption = []
useroption += [Option("user_option_1", "editpwd", "c", "img/changepwd_opt.png")]

authenticators = []

def create_user(name, email="", groups="", pwd="", option=""):
    if not pwd:
        pwd = config.get("user.passwd")
    users = tree.getRoot("users")
    user = tree.Node(name=name, type="user")
    user.set("email", email)
    user.set("password", md5.md5(pwd).hexdigest())
    user.set("opts", option)

    for group in groups.split(","):
        g = usergroups.getGroup(group)
        g.addChild(user)

    users.addChild(user)
    return user

""" load all users from db """
def loadUsersFromDB():
    users = tree.getRoot("users")
    return users.getChildren()

""" returns user object from db """
def getExternalUser(name):
    users = getExternalUserFolder()
    try:
        return users.getChild(name)
    except tree.NoSuchNodeError:
        return None

""" returns user object from db """
def getUser(id):
    users = tree.getRoot("users")
    
    if id.isdigit():
        return tree.getNode(id)
    else:
        try:
            return users.getChild(id)
        except tree.NoSuchNodeError,e:
            # try external user
            return getExternalUser(id)

def doExternalAuthentification(name, pwd):
    global authenticators
    for a in authenticators:
        if a(name,pwd):
            return 1
    return 0

def getUserFromRequest(req):
    try:
        user = req.session["user"]
    except KeyError:
        user = getUser(config.get("user.guestuser"))
        if not user:
            raise "User not found: \"" + config.get("user.guestuser")+"\""
    return user

def getExternalUserFolder():
    try:
        extusers = tree.getRoot("external_users")
    except tree.NoSuchNodeError:
        extusers = tree.Node("external_users", "users")
        tree.getRoot().addChild(extusers)
    return extusers

extuser_lock = thread.allocate_lock()

def checkLogin(name, pwd):
    user = getUser(name)
    digest1 = md5.md5(pwd).hexdigest()
    if user:
        if digest1 == user.getPassword():
            return 1
    else:
        user = getExternalUser(name)
        if user:
            if digest1 == user.getPassword():
                return 1

    if doExternalAuthentification(name, pwd):
        # if an external authenticator was able to log this
        # user in, store the user name and hashed password
        # in our database, so we recognize this person
        # from now on (and can display him in the admin
        # area).
        # potential security problem: if a local user has
        # the same name as some other external
        # user, that external user can log in using his own
        # password (and overwrite the internal password). 
        # This only happens if the names (user ids) are not 
        # the email addresses, however.
        if user:
            # overwrite password by the one used for
            # the external authentication, so the next
            # login is faster.
            user.set("password", md5.md5(pwd).hexdigest())
        else:
            extusers = getExternalUserFolder()
            user = tree.Node(name=name, type="user")
            if '@' in name:
                user.set("email", name)
            user.set("password", md5.md5(pwd).hexdigest())
            user.set("opts", '')

            extuser_lock.acquire()
            try:
                if not extusers.hasChild(name):
                    extusers.addChild(user)
            finally:
                extuser_lock.release()
        return 1

def changePWD(name, pwd):
    user = getUser(name)
    user.setPassword(md5.md5(pwd).hexdigest())
        
""" add new user in db """
def addUser(user):
    global conn
    tmp = ""
    for grp in user.getGroups():
        tmp += grp + ","
    user.setGroups(tmp[:-1])
    conn.addUser(user)    

def update_user(name, email, groups, option, new_name=""):
    user = getUser(name)
    user.set("email", email)
    user.set("opts", option)
    if new_name!="":
        user.setName(new_name)
    # remove user from all groups
    for p in user.getParents():
        if p.type == "usergroup":
            p.removeChild(user)
    # add user to the "new" groups
    for group in groups.split(","):
        g = usergroups.getGroup(group)
        g.addChild(user)


""" delete user from db """
def deleteUser(user):
    for group in tree.getRoot("usergroups").getChildren():
        for guser in group.getChildren():
            if guser.getName()==user.getName():
                group.removeChild(guser)
    users = tree.getRoot("users")
    users.removeChild(user)
                
    for c in tree.getRoot("home").getChildren():
        if c.getAccess("read").find("{user "+user.getName()+"}")>=0 and c.getAccess("write").find("{user "+user.getName()+"}")>=0:
            tree.getRoot("home").removeChild(c)
            break
        


""" check if user with given name still existing in db """
def existUser(username):
    return getUser(username) != None

def makeRandomPassword():
    a = "abcdfghijklmnopqrstuvwxyz"
    c = "bcdfghjklmnpqrstvwxyz"
    v = "aeiuo"
    i = "0123456789"
    char1 = c[random.randint(0,len(c)-1)]
    char2 = v[random.randint(0,len(v)-1)]
    char3 = c[random.randint(0,len(c)-1)]
    nr1 = i[random.randint(0,len(i)-1)]
    nr2 = i[random.randint(0,len(i)-1)]
    char4 = a[random.randint(0,len(a)-1)]
    return char1+char2+char3+nr1+nr2+char4

def registerAuthenticator(auth):
    global authenticators
    authenticators += [auth]

