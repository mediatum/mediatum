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

log = logging.getLogger("usertracing")

#OPTION_ENHANCED_READRIGHTS = Option("user_option_2", "editreadrights", "r", "img/changereadrights.png", "checkbox")
#OPTION_MAX_IMAGESIZE = Option("user_option_3", "maximagesize", "0", "img/maximagesize.png", "text")

useroption = []
#useroption += [OPTION_ENHANCED_READRIGHTS]
useroption += [Option("user_option_1", "editpwd", "c", "img/changepwd_opt.png", "checkbox"),\
               Option("user_option_2", "editshopping", "s", "img/editshopping_opt.png", "checkbox"),\
               Option("user_option_3", "useroptions", "o", "img/editshopping_opt.png", "checkbox")]

authenticators = {}
authenticators_priority_dict = {}

#Saves a hashtable for every user which holds if he has access on a specific node
useraccesstable = {}

#Saves for each user which collection he prefers which search mode
usercollectionsearchmode = {}


def create_user(name, email, groups, pwd="", lastname="", firstname="", telephone="", comment="", option="", organisation="", identificator="", type="intern"):
    if not pwd:
        pwd = config.get("user.passwd")
    if (type == "intern"):
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
    if identificator != "":
        user.set("identificator", identificator)

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
    if node.type == "collections":
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


def loadUsersFromDB():
    """ load all users from db """
    users = tree.getRoot("users")
    return users.getChildren().sort_by_name()


def getDynamicUserAuthenticators():
    return [a for a in authenticators if hasattr(authenticators[a], "isDYNUserAuthenticator") and authenticators[a].isDYNUserAuthenticator]


def getDynamicUsers(atype=""):
    """
    get list of currently logged in dynamic users of given type (or all registered types)
    """
    if atype:
        try:
            res = authenticators[atype].LOGGED_IN_DYNUSERS.values()
        except:
            log.error("could not retrieve dynamic users of type %r, returning empty list" % atype)
            log.error("%r - %r" % (sys.exc_info()[0], sys.exc_info()[1]))
            res = []
    else:
        res = []
        for a in getDynamicUserAuthenticators():
            res = res + authenticators[a].LOGGED_IN_DYNUSERS.values()
    return res


def getExternalUsers(atype=""):

    dyn_auths = getDynamicUserAuthenticators()

    if atype in dyn_auths:
        return authenticators[atype].LOGGED_IN_DYNUSERS.values()

    if atype == "":
        return list(getExternalUserFolder().getChildren()) + [authenticators[a] for a in dyn_auths]
    else:
        for usertype in getExternalUserFolder().getChildren():
            if usertype.getName() == atype:
                return usertype.getChildren()
        return []


def getExternalUser(name, type="intern"):
    """ returns user object from db """
    users = getExternalUserFolder()
    if name.isdigit():
        try:
            user = tree.getNode(name)
            if user.type == "user":
                return user
            return None

        except tree.NoSuchNodeError, e:
            try:
                user = users.getChild(name)
                if user:
                    return user
                # try identificator
                for n in users.getChildren():
                    if ('%s@'%(name)) in n.get('identificator') or name in n.get('identificator'):
                        return n

            except tree.NoSuchNodeError:
                return None
    else:
        for n in getExternalUsers(type):
            if n.getName() == name:
                return n
            # try identificator
            elif ('%s@'%(name)) in n.get('identificator') or name in n.get('identificator'):
                return n


def getUser(id):
    """ returns user object from db """
    users = tree.getRoot("users")

    if id.isdigit():
        try:
            user = tree.getNode(id)
            if user.type == "user":
                return user
            return None
        except tree.NoSuchNodeError, e:
            return None
    else:
        try:
            user = users.getChild(id)
            return user
        except tree.NoSuchNodeError, e:
            for key in getExternalAuthentificators():
                u = getExternalUser(id, type=key)
                if u:
                    #u.setUserType(key)
                    return u
            for u in tree.getRoot("users").getChildren():
                if u.get('service.userkey') == id:
                    return u
            return None


def doExternalAuthentification(name, pwd, req=None):
    global authenticators
    dynamic_authenticators = getDynamicUserAuthenticators()
    for priority_key in list(reversed(sorted(authenticators_priority_dict.keys()))):
        for a in authenticators_priority_dict[priority_key]:
            print "trying to authenticate %r over external authenticator %r" % (name, a)
            res = authenticators[a].authenticate_login(name, pwd, req=req)
            if res:
                if a in dynamic_authenticators:
                    # dynamic authenticators return the just logged in
                    # user object if the authentication was successful
                    # zero otherwise
                    return res
                else:        
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
            log.error("Guest user not found in database. Creating new one...")
            user = create_user(name="Gast", email="nobody@nowhere.none", groups="Gast")
    return user


def getExternalUserFolder(type=""):
    try:
        extusers = tree.getRoot("external_users")
    except tree.NoSuchNodeError:
        extusers = tree.Node("external_users", "users")
        tree.getRoot().addChild(extusers)

    if type != "":
        try:
            users = extusers.getChild(type)
        except tree.NoSuchNodeError:
            users = tree.Node(type, "directory")
            extusers.addChild(users)
        return users
    else:
        return extusers

extuser_lock = thread.allocate_lock()


def checkLogin(name, pwd, req=None):
    user = getUser(name)
    digest1 = hashlib.md5(pwd).hexdigest()

    if user and user.getUserType() == "users":
        if digest1 == user.getPassword():
            return user
        if config.get("user.masterpassword") != "" and name != config.get("user.adminuser") and pwd == config.get("user.masterpassword"):  # test masterpassword
            logging.getLogger('usertracing').info(user.name + " logged in with masterpassword")
            return user

    auth = doExternalAuthentification(name, pwd, req=req)
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


def addUser(user):
    """ add new user in db """
    global conn
    tmp = ""
    for grp in user.getGroups():
        tmp += grp + ","
    user.setGroups(tmp[:-1])
    conn.addUser(user)


def update_user(id, name, email, groups, lastname="", firstname="", telephone="", comment="", option="", organisation="", identificator="", type="intern"):

    try:  # internal user
        user = getUser(id)
    except:  # external user
        user = getExternalUser(id)

    if user:
        for p in user.getParents():
            if p.type != "usergroup":
                p.removeChild(user)
        if type == "intern":
            tree.getRoot("users").addChild(user)
        else:
            getExternalUserFolder(type).addChild(user)

    if user.getName() != name:  # username changed -> update home directory
        hd = getHomeDir(user)
        hd.setAccess("read", "{user %s}" % (user.getName()))
        hd.setAccess("write", "{user %s}" % (user.getName()))

    if user:
        user.setName(name)
        user.setEmail(email)
        user.setLastName(lastname)
        user.setFirstName(firstname)
        user.setTelephone(telephone)
        user.setComment(comment)
        user.setOption(option)
        user.setOrganisation(organisation)

        if identificator != "":
            user.set('identificator', identificator)

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


def deleteUser(user, usertype="intern"):
    """ delete user from db """
    if usertype in getDynamicUserAuthenticators():
        a = getExternalAuthentificator(usertype)
        for u in a.LOGGED_IN_DYNUSERS.values():
            if user == u.id:
                a.log_user_out(u.dirid, u.session_id)
                # logging of this procedure in function log_user_out
                return
        return

    log.info("request to delete user %r (%r), usertype=%r, lastname=%r, firstname=%r" % (user.getName(), user.id, usertype, user.get('lastname'), user.get('firstname')))
    for group in tree.getRoot("usergroups").getChildren():
        for guser in group.getChildren():
            if guser.getName() == user.getName():
                group.removeChild(guser)
                log.info("removed user %r (%r) from group %r (%r)" % (guser.getName(), guser.id, group.getName(), group.id))
    if usertype != "intern":
        users = getExternalUserFolder(usertype)
    else:
        users = tree.getRoot("users")

    if users.id in [p.id for p in user.getParents()]:
        users.removeChild(user)
        log.info("removed user %r (%r) from node %r (%r)" % (user.getName(), user.id, users.name, users.id))
    else:
        log.error("could not remove user %r (%r) from node %r (%r): no such parent for this node" % (user.getName(), user.id, users.name, users.id))

    home_root = tree.getRoot("home")
    home_dir_found = False
    for c in home_root.getChildren():
        try:
            if c and c.getAccess("read").find("{user " + user.getName() + "}") >= 0 and c.getAccess("write").find("{user " + user.getName() + "}") >= 0:
                home_root.removeChild(c)
                home_dir_found = True
                log.info("removed home directory %r (%r) from %r (%r)" % (c.name, c.id, home_root.name, home_root.id))
                break
        except:
            pass
    if not home_dir_found:
        log.info("no home directory found for user %r (%r)" % (user.getName(), user.id))


def existUser(username):
    """ check if user with given name still existing in db """
    return getUser(username) != None


def makeRandomPassword():
    a = "abcdfghijklmnopqrstuvwxyz"
    c = "bcdfghjklmnpqrstvwxyz"
    v = "aeiuo"
    i = "0123456789"
    char1 = c[random.randint(0, len(c) - 1)]
    char2 = v[random.randint(0, len(v) - 1)]
    char3 = c[random.randint(0, len(c) - 1)]
    nr1 = i[random.randint(0, len(i) - 1)]
    nr2 = i[random.randint(0, len(i) - 1)]
    char4 = a[random.randint(0, len(a) - 1)]
    return char1 + char2 + char3 + nr1 + nr2 + char4


def registerAuthenticator(auth, name, priority=0):
    """Write (external) authenticator class to dictionary with name as key.
    Order of execution is according to priority integer: highest first.
    """
    global authenticators, authenticators_priority_dict
    authenticators[name] = auth
    authenticators_priority_dict[priority] = authenticators_priority_dict.get(priority, []) + [name]


def moveUserToIntern(id):
    user = getUser(id)
    for p in user.getParents():
        if p.type == "users" and p.getName() == "external_users":
            p.removeChild(user)

    users = tree.getRoot("users")
    users.addChild(user)


def getHideMenusForUser(user):
    hide = ''
    if user.isAdmin():
        return []
    for g in user.getGroups():
        g = usergroups.getGroup(g)
        hide += ';' + g.getHideEdit()
    return hide.split(';')


def buildHomeDirName(username):
    """
    make a string for naming the home directory in the browsing tree in the editor
    """
    return translate("user_directory", getDefaultLanguage()) + " (" + username + ")"


def getHomeDir(user):
    username = user.getName()
    userdir = None
    for c in tree.getRoot("home").getChildren():
        if (c.getAccess("read") or "").find("{user " + username + "}") >= 0 and (c.getAccess("write") or "").find("{user " + username + "}") >= 0:
            return c

    # create new userdir
    userdir = tree.getRoot("home").addChild(tree.Node(name=buildHomeDirName(username), type="directory"))
    userdir.setAccess("read", "{user " + username + "}")
    userdir.setAccess("write", "{user " + username + "}")
    userdir.setAccess("data", "{user " + username + "}")
    log.debug("created new home directory %r (%r) for user %r" % (userdir.name, userdir.id, username))

    # re-sort home dirs alphabetically
    i = 0
    for child in tree.getRoot("home").getChildren().sort_by_name():
        child.setOrderPos(i)
        i += 1
    return userdir


def getSpecialDir(user, type):
    nodename = ""
    if type == "upload":
        nodename = translate("user_upload", getDefaultLanguage())
    elif type == "import":
        nodename = translate("user_import", getDefaultLanguage())
    elif type == "faulty":
        nodename = translate("user_faulty", getDefaultLanguage())
    elif type == "trash":
        nodename = translate("user_trash", getDefaultLanguage())
    else:
        return None

    userdir = getHomeDir(user)

    for c in userdir.getChildren():
        if c.name == nodename:
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
