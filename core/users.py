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
import hashlib
import core.tree as tree
import core.translation
import random
import thread
import logging

from utils.utils import Option
from core.translation import getDefaultLanguage, translate

#OPTION_ENHANCED_READRIGHTS = Option("user_option_2", "editreadrights", "r", "img/changereadrights.png", "checkbox")
#OPTION_MAX_IMAGESIZE = Option("user_option_3", "maximagesize", "0", "img/maximagesize.png", "text")

useroption = []
#useroption += [OPTION_ENHANCED_READRIGHTS]
useroption += [Option("user_option_1", "editpwd", "c", "img/changepwd_opt.png", "checkbox"),\
               Option("user_option_2", "editshopping", "s", "img/editshopping_opt.png", "checkbox")]

authenticators = {}

#Saves a hashtable for every user which holds if he has access on a specific node...
useraccesstable = {}

#Saves for each user which collection he prefers which search mode
usercollectionsearchmode = {}

def create_user(name, email, groups, pwd="", lastname="", firstname="", telephone="", comment="", option="", organisation="", type="intern"):    
    if not pwd:
        pwd = config.get("user.passwd")
    if (type=="intern"):
        users = tree.getRoot("users")
    else:
        users = getExternalUserFolder(type)
    
    user = tree.Node(name=name, type="user")
    user.set("email", email)
    user.set("password", hashlib.md5(pwd).hexdigest())
    user.set("opts", option)
    user.set("lastname", lastname)
    user.set("firstname", firstname)
    user.set("telephone", telephone)
    user.set("comment", comment)
    user.set("organisation", organisation)

    for group in groups.split(","):
        g = usergroups.getGroup(group)
        g.addChild(user)

    users.addChild(user)
    return user

# Methods for manipulation of access hashtable
def getAccessTable(user):
    if not useraccesstable.has_key(user.id):
        useraccesstable[user.id] = {}
    return useraccesstable[user.id]

def clearAllTableAccess():
    """ Clears the complete cache """
    allkeys = useraccesstable.keys()
    for k in allkeys:
        useraccesstable[k].clear()

        
def clearTableAccess(user):
    """Clears all entries from a hashtable"""
    try:
        getAccessTable(user).clear()
    except:                         
        sys.exc_info()[0]

        
def getCollectionSearchMode(user, collectionid):
    """ Returns -1, is current user has no search mode specified for a collection"""
    if (usercollectionsearchmode.has_key(user)):
        if (usercollectionsearchmode[user].has_key(collectionid)):
            return usercollectionsearchmode[user][collectionid]
    return -1

    
def setCollectionSearchMode(user, collectionid, searchmode):
    if (not usercollectionsearchmode.has_key(user)):
        usercollectionsearchmode[user] = {}
    usercollectionsearchmode[user][collectionid] = searchmode


def setTableAccess(user, node, access):
    """Sets the rights of a node"""
    if node.type=="collections":
        return
    getAccessTable(user)[node.id] = access

    
def setTableAccessWithParents(user, node, access):
    """Sets the rights of a node and its direct parents"""
    setTableAccess(user, node, access)
    for p in node.getParents():
        if p.type != "collections":
            setTableAccess(user, p, access)

            
def getTableAccess(user, node):
    """Retrieves the access rights of a node. Returns 0, if there are either no rights available or the node has no rights"""
    accesstable = getAccessTable(user)
    if accesstable.has_key(node.id):
        return accesstable[node.id]
    return 0


def hasTableAccess(user, node):
    """Checks if the user has access on a specific node and if he is even allowed to use the hashtable """
    return getAccessTable(user).has_key(node.id)
# End of methods for access hashtable manipulation
   
    
""" load all users from db """
def loadUsersFromDB():
    users = tree.getRoot("users")
    return users.getChildren().sort(field="name")
    
def getExternalUsers(type=""):
    if type=="":
        return getExternalUserFolder().getChildren()
    else:
        for usertype in getExternalUserFolder().getChildren():
            if usertype.getName()==type:
                return usertype.getChildren()
        return []
    
""" returns user object from db """
def getExternalUser(name, type="intern"):
    users = getExternalUserFolder()
    if name.isdigit():
        try:
            return tree.getNode(name)
        except tree.NoSuchNodeError,e:
            try:
                return users.getChild(name)
            except tree.NoSuchNodeError:
                return None
    else:
        for n in getExternalUsers(type):
            if n.getName()==name:
                return n
        

""" returns user object from db """
def getUser(id):
    users = tree.getRoot("users")
    
    if id.isdigit():
        try:
            #return tree.getNode(id)
            user = tree.getNode(id)
            user.setUserType("intern")
            return user
        except tree.NoSuchNodeError,e:
            return None
    else:
        try:
            #return users.getChild(id)
            user = users.getChild(id)
            user.setUserType("intern")
            return user
        except tree.NoSuchNodeError,e:
            for key in getExternalAuthentificators():
                u = getExternalUser(id, type=key)
                if u:
                    u.setUserType(key)
                    return u
            return None

def doExternalAuthentification(name, pwd):
    global authenticators
    for a in authenticators:
        #x = authenticators[a].authenticate_login(name,pwd)#==1:
        if authenticators[a].authenticate_login(name,pwd):
            return authenticators[a].getUser(name)
    return None
    
def getExternalAuthentificator(name):
    global authenticators
    if name in authenticators.keys():
        return authenticators[name]
    return None

def getExternalAuthentificators():
    global authenticators
    return authenticators
  

def getUserFromRequest(req):
    try:
        user = req.session["user"]
        if not user:
            raise KeyError()
    except KeyError:
        user = getUser(config.get("user.guestuser"))
        if not user:
            raise "User not found: \"" + config.get("user.guestuser")+"\""
    return user

def getExternalUserFolder(type=""):
    try:
        extusers = tree.getRoot("external_users")
    except tree.NoSuchNodeError:
        extusers = tree.Node("external_users", "users")
        tree.getRoot().addChild(extusers)
        
    if type!="":
        try:
            users = extusers.getChild(type)
        except tree.NoSuchNodeError:
            users = tree.Node(type, "directory")
            extusers.addChild(users)
        return users
    else: 
        return extusers

extuser_lock = thread.allocate_lock()

def checkLogin(name, pwd):
    user = getUser(name)
    digest1 = hashlib.md5(pwd).hexdigest()

    if user and user.getUserType()=="intern":
        if digest1==user.getPassword():
            return user
        if config.get("user.masterpassword")!="" and name!="Administrator" and pwd==config.get("user.masterpassword"): # test masterpassword
            logging.getLogger('usertracing').info(user.name + " logged in with masterpassword")
            return user
        
    auth = doExternalAuthentification(name, pwd)
    #if doExternalAuthentification(name, pwd):
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
        
    if auth:
        return auth
    else:
        return None
    
    
    if auth[0]:
        if user:
            # overwrite password by the one used for
            # the external authentication, so the next
            # login is faster.
            user.set("password", hashlib.md5(pwd).hexdigest())
        else:
            extusers = getExternalUserFolder()
            user = tree.Node(name=name, type="user")
            if '@' in name:
                user.set("email", name)
            user.set("password", hashlib.md5(pwd).hexdigest())
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
    user.setPassword(hashlib.md5(pwd).hexdigest())
        
""" add new user in db """
def addUser(user):
    global conn
    tmp = ""
    for grp in user.getGroups():
        tmp += grp + ","
    user.setGroups(tmp[:-1])
    conn.addUser(user)    


def update_user(id, name, email, groups, lastname="", firstname="", telephone="", comment="", option="", organisation="", type="intern"):
    if type=="intern":
        user = getUser(id)
    else:
        user = getExternalUser(id, type)
    if user:
        user.setName(name)
        user.setEmail(email)
        user.setLastName(lastname)
        user.setFirstName(firstname)
        user.setTelephone(telephone)
        user.setComment(comment)
        user.setOption(option)
        user.setOrganisation(organisation)

        # remove user from all groups
        for p in user.getParents():
            if p.type == "usergroup":
                p.removeChild(user)
        # add user to the "new" groups
        for group in groups.split(","):
            g = usergroups.getGroup(group)
            g.addChild(user)
    else:
        print "user not found"
    return user

""" delete user from db """
def deleteUser(user, usertype="intern"):
    for group in tree.getRoot("usergroups").getChildren():
        for guser in group.getChildren():
            if guser.getName()==user.getName():
                group.removeChild(guser)
    if usertype!="intern":
        users = getExternalUserFolder(usertype)
    else:
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

def registerAuthenticator(auth, name):
    global authenticators
    authenticators[name] = auth
    
def moveUserToIntern(id):
    user = getUser(id)
    for p in user.getParents():
        if p.type == "users" and p.getName()=="external_users":
            p.removeChild(user)
            
    users = tree.getRoot("users")
    users.addChild(user)

def getHideMenusForUser(user):
    hide = ''
    for g in user.getGroups():
        g = usergroups.getGroup(g)
        hide += ';'+g.getHideEdit()
    return hide.split(';')
    
def getHomeDir(user):
    username = user.getName()
    userdir = None
    for c in tree.getRoot("home").getChildren():
        if (c.getAccess("read") or "").find("{user "+username+"}")>=0 and (c.getAccess("write") or "").find("{user "+username+"}")>=0:
            return c
            
    # create new userdir
    userdir = tree.getRoot("home").addChild(tree.Node(name=translate("user_directory", getDefaultLanguage())+" ("+username+")", type="directory"))
    userdir.setAccess("read","{user "+username+"}")
    userdir.setAccess("write","{user "+username+"}")
    userdir.setAccess("data","{user "+username+"}")
    
    # re-sort home dirs alphabetically
    i = 0
    for child in tree.getRoot("home").getChildren().sort("name"):
        child.setOrderPos(i)
        i += 1
    return userdir
    
    
def getSpecialDir(user, type):
    nodename = ""
    if type=="upload":
        nodename = translate("user_upload", getDefaultLanguage())
    elif type=="import":
        nodename = translate("user_import", getDefaultLanguage())
    elif type=="faulty":
        nodename = translate("user_faulty", getDefaultLanguage())
    elif type=="trash":
        nodename = translate("user_trash", getDefaultLanguage())
    else:
        return None

    userdir = getHomeDir(user)

    for c in userdir.getChildren():
        if c.name==nodename:
            return c
    # create new directory
    return userdir.addChild(tree.Node(name=nodename, type="directory"))
    
    
def getUploadDir(user):
    return getSpecialDir(user, "upload")
    
def getImportDir(user):
    return getSpecialDir(user, "import")
    
def getFaultyDir(user):
    return getSpecialDir(user, "faulty")

def getTrashDir(user):
    return getSpecialDir(user, "trash")
