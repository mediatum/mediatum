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
import sys
import traceback
import logging
import re
import datetime
import time

import core.config as config
import core.tree as tree
import core.acl as acl
import core.users as users
from utils.utils import getAllCollections, formatException
import utils.mail as mail
from core.usergroups import loadGroupsFromDB
from core.users import (loadUsersFromDB, useroption, getUser, update_user, existUser, create_user, makeRandomPassword, deleteUser,
                        getExternalUsers, getExternalUser, moveUserToIntern, getExternalAuthentificators, getDynamicUserAuthenticators)
from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from core.translation import lang, t


log = logging.getLogger("usertracing")
users_cache = []


def getInformation():
    return {"version": "1.0"}


def fill_users_cache(verbose=True):
    global users_cache
    atime = time.time()
    internal_users = loadUsersFromDB()
    if verbose:
        log.info("%.3f sec. to load %r internal users" % (time.time() - atime, len(internal_users)))
        atime = time.time()
    res = internal_users
    for usertype in list(getExternalUsers()):
        # this loop will also loop the dynamic authenticators
        ext_users = list(usertype.getChildren())
        res += ext_users
        if verbose:
            log.info("%.3f sec. to load %r external users of type %r" % (time.time() - atime, len(ext_users), usertype.name))
            atime = time.time()
    users_cache = res


def flush_users_cache(verbose=True):
    global users_cache
    if verbose:
        log.debug("going to empty users_cache, which has %r entries" % (len(users_cache)))
    users_cache = []


def searchUser(value):
    global users_cache
    atime = time.time()
    res = []
    value = value.lower().split("*")

    if 1:  # always reload users_cache #len(users_cache)<1:
        fill_users_cache(verbose=True)
        users = users_cache
    else:
        users = users_cache

    for user in users:
        user_data = user.getName().lower() + ("").join([str(i[1]).lower().strip() for i in user.items()])

        n_found = 0
        for v in value:  # test each value
            if v not in user_data:
                n_found += 1
        if n_found == 0:
            res.append(user)
    log.debug("searchUser: %.3f sec. for value=%r, found %r users" % (time.time() - atime, value, len(res)))
    return res


def validate(req, op):
    """standard validator"""
    global users_cache
    try:

        if "style" in req.params:
            req.write(view(req))
            return ""

        for key in req.params.keys():
            if key.startswith("new"):
                # create new user
                return editUser_mask(req, "")

            elif key.startswith("edit_"):
                # edit user
                return editUser_mask(req, str(key[key.index("_") + 1:-2]))

            elif key.startswith("sendmail_") and req.params.get("form_op", "") != "cancel":
                # send email
                return sendmailUser_mask(req, str(key[key.index("_") + 1:-2]))

            elif key.startswith("delete_"):
                # delete user
                user_from_request = users.getUserFromRequest(req)
                username_from_form = key[7:-2]
                dyn_auths = getDynamicUserAuthenticators()
                isDynamic = False
                for dyn_auth in dyn_auths:
                    if username_from_form.startswith(dyn_auth + "|"):
                        isDynamic = (username_from_form, dyn_auth)
                        break
                if isDynamic:
                    log.info("%r is requesting logout of dynamic user %r (%r)" % (user_from_request.getName(), isDynamic[0], isDynamic[1]))
                    deleteUser(isDynamic[0], isDynamic[1])
                else:
                    usertype = req.params.get("usertype", "intern")
                    usernode = getUser(key[7:-2])
                    if not usertype.strip():
                        usertype = usernode.getUserType()
                        if usertype == 'users':
                            # function deleteUser expects usertype='intern'
                            # for children if root->users, but getUserType()
                            # returns 'users' for those
                            usertype = 'intern'
                    log.info("%r is requesting deletion of user %r (%r, %r)" %
                             (user_from_request.getName(), usernode.name, usernode.id, usertype))
                    deleteUser(usernode, usertype=usertype)
                    del_index = users_cache.index(usernode)

                    del users_cache[del_index]

                searchterm_was = req.params.get("searchterm_was", "")
                if searchterm_was:
                    req.params['action'] = 'search'
                    req.params['searchterm'] = searchterm_was
                    req.params['use_macro'] = 'view'
                    req.params['execute_search'] = searchterm_was

                break

            elif key.startswith("tointern_"):
                moveUserToIntern(key[9:-2])
                break

            elif key.startswith("reset_"):
                # reset password
                if req.params["change_passwd"] != "":
                    getUser(key[6:-2]).resetPassword(req.params["change_passwd"])
                else:
                    getUser(key[6:-2]).resetPassword(config.settings["user.passwd"])
                break

        if "form_op" in req.params.keys():
            _option = ""
            for key in req.params.keys():
                if key.startswith("option_"):
                    _option += key[7]

            if req.params.get("form_op") == "save_new":
                # save user values
                if req.params.get("username", "") == "" or req.params.get("usergroups", "") == "" or req.params.get("email", "") == "":
                    return editUser_mask(req, "", 1)  # no username or group selected
                elif existUser(req.params.get("username")):
                    return editUser_mask(req, "", 2)  # user still existing
                else:
                    create_user(
                        req.params.get("username"),
                        req.params.get("email"),
                        req.params.get("usergroups").replace(
                            ";",
                            ","),
                        pwd=req.params.get(
                            "password",
                            ""),
                        lastname=req.params.get(
                            "lastname",
                            ""),
                        firstname=req.params.get("firstname"),
                        telephone=req.params.get("telephone"),
                        comment=req.params.get("comment"),
                        option=_option,
                        organisation=req.params.get(
                            "organisation",
                            ""),
                        identificator=req.params.get(
                            "identificator",
                            ""),
                        type=req.params.get(
                            "usertype",
                            "intern"))

            elif req.params["form_op"] == "save_edit":
                # update user
                if req.params.get("email", "") == "" or req.params.get("username", "") == "" or req.params.get("usergroups", "") == "":
                    return editUser_mask(req, req.params.get("id"), 1)  # no username, email or group selected
                else:
                    update_user(
                        req.params.get(
                            "id",
                            0),
                        req.params.get(
                            "username",
                            ""),
                        req.params.get(
                            "email",
                            ""),
                        req.params.get(
                            "usergroups",
                            "").replace(
                            ";",
                            ","),
                        lastname=req.params.get("lastname"),
                        firstname=req.params.get("firstname"),
                        telephone=req.params.get("telephone"),
                        comment=req.params.get("comment"),
                        option=_option,
                        organisation=req.params.get(
                            "organisation",
                            ""),
                        identificator=req.params.get(
                            "identificator",
                                ""),
                        type=req.params.get(
                            "usertype",
                            "intern"))

            flush_users_cache()
        return view(req)
    except:
        print "Warning: couldn't load module for type", type
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])


def view(req):
    """show all users"""
    global users_cache

    users = []
    order = getSortCol(req)
    actfilter = getFilter(req)
    showdetails = 0
    searchterm_was = ""
    macro = "view"

    usertype = req.params.get("usertype", "")

    if "action" in req.params:
        macro = "details"

        if req.params.get("action") == "details":  # load all users of given type

            if 1:  # len(users_cache)<1: # load users in cache
                # always load users anew: cache-update for dynamic users seems
                # uneconomic: loading users seems to run fast
                users = list(loadUsersFromDB())
                for _usertype in list(getExternalUsers()):
                    users += list(_usertype.getChildren())
                users_cache = users
            else:  # use users from cache
                users = users_cache

            if req.params.get("usertype") == "intern":
                users = filter(lambda x: x.getUserType() == 'users', users)
            elif req.params.get("usertype") == "all":
                pass
            else:
                users = filter(lambda x: x.getUserType() == req.params.get("usertype"), users)

        elif req.params.get("action") == "search":  # load all users with matching search
            req.params["page"] = "0"
            searchterm = req.params.get('searchterm')
            users = searchUser(searchterm)
            if searchterm:
                searchterm_was = searchterm
                if 'use_macro' in req.params:
                    if "searchterm_was" in req.params and searchterm == req.params.get("searchterm_was"):
                        macro = req.params.get('use_macro')

    elif "actpage" in req.params or "actfilter" in req.params or "filterbutton" in req.params:
        users = users_cache
        showdetails = 1
        if "cancel" in req.params:
            showdetails = 0

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", t(lang(req), "admin_filter_all")):
            None
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            if req.params.get("filtertype", "") == "username":
                users = filter(lambda x: num.match(x.getName()), users)
            else:
                users = filter(lambda x: num.match(x.get("lastname")), users)
        elif actfilter == "else" or actfilter == t(lang(req), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            if req.params.get("filtertype", "") == "username":
                users = filter(lambda x: not all.match(x.getName()), users)
            else:
                users = filter(lambda x: not all.match(x.get("lastname")), users)
        else:
            if req.params.get("filtertype", "") == "username":
                users = filter(lambda x: x.getName().lower().startswith(actfilter), users)
            else:
                users = filter(lambda x: x.get("lastname").lower().startswith(actfilter), users)

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            users.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))
        elif int(order[0:1]) == 1:
            users.sort(lambda x, y: cmp(x.getLastName().lower(), y.getLastName().lower()))
        elif int(order[0:1]) == 2:
            users.sort(lambda x, y: cmp(x.getFirstName().lower(), y.getFirstName().lower()))
        elif int(order[0:1]) == 3:
            users.sort(lambda x, y: cmp(x.getEmail().lower(), y.getEmail().lower()))
        elif int(order[0:1]) == 4:
            users.sort(lambda x, y: cmp(x.getOrganisation(), y.getOrganisation()))
        elif int(order[0:1]) == 5:
            users.sort(lambda x, y: cmp(x.getGroups(), y.getGroups()))
        elif int(order[0:1]) == 6:
            users.sort(lambda x, y: cmp(x.stdPassword(), y.stdPassword()))
        if int(order[1:]) == 1:
            users.reverse()
    else:
        users.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))

    def getUsers(req, users):
        if req.params.get("usertype") == "intern":
            users = filter(lambda x: x.getUserType() == 'users', users)
        elif req.params.get("usertype") == "all":
            pass
        else:
            users = filter(lambda x: x.getUserType() == req.params.get("usertype"), users)
        return users

    if usertype:
        users = getUsers(req, users)
    pages = Overview(req, users)
    v = pages.getStdVars()
    v["filterattrs"] = [("username", "admin_user_filter_username"), ("lastname", "admin_user_filter_lastname")]
    v["filterarg"] = req.params.get("filtertype", "username")
    v["sortcol"] = pages.OrderColHeader([t(lang(req), "admin_user_col_" + str(i)) for i in range(1, 9)])

    v["options"] = list(useroption)
    v["users"] = users
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["auth"] = getExternalAuthentificators()
    v["details"] = showdetails

    v["language"] = lang(req)
    v["t"] = t
    v["now"] = datetime.datetime.now
    v["usertype"] = usertype
    v["id_func"] = id  # make sure, this is the python built-in
    v["searchterm_was"] = searchterm_was
    v["execute_search"] = req.params.get("execute_search", "")

    return req.getTAL("web/admin/modules/user.html", v, macro=macro)

#
# edit/create user
#


def editUser_mask(req, id, err=0):
    ugroups = []
    usertype = req.params.get("usertype", "intern")
    newuser = 0

    if err == 0 and id == "":  # new user
        user = tree.Node("", type="user")
        user.setOption("c")
        newuser = 1

    elif err == 0 and id != "":  # edit user
        if usertype == "intern":
            user = getUser(id)
        else:
            user = getExternalUser(id)
    else:
        # error while filling values
        option = ""
        for key in req.params.keys():
            if key.startswith("option_"):
                option += key[7]

        for usergroup in req.params.get("usergroups", "").split(";"):
            ugroups += [usergroup]

        user = tree.Node("", type="user")
        user.setName(req.params.get("username", ""))
        user.setEmail(req.params.get("email", ""))
        user.setOption(option)
        user.setLastName(req.params.get("lastname", ""))
        user.setFirstName(req.params.get("firstname", ""))
        user.setTelephone(req.params.get("telephone", ""))
        user.setComment(req.params.get("comment", ""))
        user.setOrganisation(req.params.get("organisation", ""))

    v = getAdminStdVars(req)
    v["error"] = err
    v["user"] = user
    v["groups"] = loadGroupsFromDB()
    v["ugroups"] = ugroups
    v["useroption"] = useroption
    v["id"] = id
    v["usertype"] = usertype
    v["filtertype"] = req.params.get("filtertype", "")
    v["actpage"] = req.params.get("actpage")
    v["newuser"] = newuser
    v["usertypes"] = getExternalAuthentificators()
    return req.getTAL("web/admin/modules/user.html", v, macro="modify")


def addACL(username, firstname, lastname, oldusername=None):
    """unused function addACL?"""
    userrule = "( user %s )" % username
    userruledesc = username

    try:
        if (not (lastname == "" or firstname == "")):
            userruledesc = "%s, %s" % (lastname, firstname)

        if (oldusername is None):
            oldusername = username

        if acl.existRule(oldusername):
            acl.updateRule(AccessRule(username, userrule, userruledesc), oldusername, username, oldusername)
        else:
            acl.addRule(AccessRule(username, userrule, userruledesc))
    except:
        print formatException()


def sendmailUser_mask(req, id, err=0):

    v = getAdminStdVars(req)
    v["path"] = req.path[1:]

    if id in["execute", "execu"]:

        userid = req.params.get("userid")
        user = getUser(userid)
        if not user:
            path = req.path[1:].split("/")
            user = getExternalUser(userid, path[-1])

        password = makeRandomPassword()
        user.resetPassword(password)

        text = req.params.get("text")
        text = text.replace("[wird eingesetzt]", password)
        try:
            mail.sendmail(req.params.get("from"), req.params.get("email"), req.params.get("subject"), text)
        except mail.SocketError:
            print "Socket error while sending mail"
            return req.getTAL("web/admin/modules/user.html", v, macro="sendmailerror")
        return req.getTAL("web/admin/modules/user.html", v, macro="sendmaildone")

    user = getUser(id)
    if not user:
        path = req.path[1:].split("/")
        user = getExternalUser(id, path[-1])

    collections = []
    seen = {}
    access = acl.AccessData(user=user)
    for node in getAllCollections():
        if access.hasReadAccess(node):
            if access.hasWriteAccess(node):
                collections.append(node.name + " (lesen/schreiben)")
                seen[node.id] = None
    for node in tree.getRoot("collections").getChildren():
        if access.hasReadAccess(node) and node.id not in seen:
            collections.append(node.name + " (nur lesen)")
    x = {}
    x["name"] = "%s %s" % (user.getFirstName(), user.getLastName())
    if(x["name"] == ""):
        x["name"] = user.getName()
    x["host"] = config.get("host.name")
    x["login"] = user.getName()
    x["isEditor"] = user.isEditor()
    x["collections"] = list()
    x["groups"] = user.getGroups()
    x["groups"].sort()
    x["language"] = lang(req)
    x["collections"] = collections
    x["collections"].sort()

    v["mailtext"] = req.getTAL("web/admin/modules/user.html", x, macro="emailtext").strip()
    v["email"] = user.getEmail()
    v["userid"] = user.getName()
    return req.getTAL("web/admin/modules/user.html", v, macro="sendmail")
