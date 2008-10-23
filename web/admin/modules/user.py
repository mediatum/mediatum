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
import sys, types
import traceback
import core.athana as athana
import logging
import core.config as config
import core.tree as tree
import core.acl as acl
import utils.mail as mail
import core.users as users
import re

from core.usergroups import loadGroupsFromDB
from core.users import loadUsersFromDB, useroption, getUser, getExternalUser, update_user, existUser, create_user, makeRandomPassword, deleteUser, getExternalUsers, getExternalUser, moveUserToIntern, getExternalAuthentificators
from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from core.translation import lang, t

#
# standard validator
#
def validate(req, op):
    try:
        for key in req.params.keys():
            if key.startswith("new"):
                # create new user
                return editUser_mask(req, "")
                
            elif key.startswith("edit_"):
                # edit user
                print str(key[key.index("_")+1:-2])
                return editUser_mask(req, str(key[key.index("_")+1:-2]))

            elif key.startswith("sendmail_") and req.params.get("form_op","")!="cancel":
                # send email
                return sendmailUser_mask(req, str(key[key.index("_")+1:-2]))

            elif key.startswith("delete_"):
                # delete user
                deleteUser(getUser(key[7:-2]), usertype=req.params.get("usertype", "intern"))
                break
            elif key.startswith("tointern_"):
                moveUserToIntern(key[9:-2])
                break
                
            elif key.startswith("reset_"):
                # reset password
                if req.params["change_passwd"]!="":
                    getUser(key[6:-2]).resetPassword(req.params["change_passwd"])
                else:
                    getUser(key[6:-2]).resetPassword(config.settings["user.passwd"])
                break

        if "form_op" in req.params.keys():
            _option =""
            for key in req.params.keys():
                if key.startswith("option_"):
                    _option += key[7]
                        
            if req.params["form_op"] == "save_new":
                # save user values
                if req.params.get("username","")=="" or req.params.get("usergroups", "")=="" or req.params.get("email","")=="":
                    return editUser_mask(req, "", 1) # no username or group selected
                elif existUser(req.params.get("username")):
                    return editUser_mask(req, "", 2) #user still existing
                else:
                    create_user(req.params.get("username"), req.params.get("email"), req.params.get("usergroups").replace(";", ","), pwd=req.params.get("password", ""), lastname=req.params.get("lastname",""), firstname=req.params.get("firstname"), telephone=req.params.get("telephone"), comment=req.params.get("comment"), option=_option, organisation=req.params.get("organisation",""), type=req.params.get("usertype", "intern"))

            elif req.params["form_op"] == "save_edit":
                # update user
                if req.params.get("email","")=="" or req.params.get("username","")=="" or req.params.get("usergroups","")=="":
                    return editUser_mask(req, req.params.get("id"), 1) # no username, emai or group selected
                else:
                    update_user(req.params.get("id", 0), req.params.get("username",""),req.params.get("email",""), req.params.get("usergroups","").replace(";", ","), lastname=req.params.get("lastname"), firstname=req.params.get("firstname"), telephone=req.params.get("telephone"), comment=req.params.get("comment"), option=_option, organisation=req.params.get("organisation",""), type=req.params.get("usertype", "intern"))

        return view(req)
    except:
        print "Warning: couldn't load module for type",type
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])


#
# show all users
#
def view(req):
    global useroption
    path = req.path[1:].split("/")
    users = list()
    usertypes = list(getExternalUsers())
    
    auth = getExternalAuthentificators()
    
    if len(path)==2:
        usertype="extern"
        for usertype in usertypes:
            if usertype.getName()==path[1]:
                users = list(usertype.getChildren())
                usertype = path[1]
                break
    else:
        users = list(loadUsersFromDB())
        usertype = "intern"

    order = getSortCol(req)
    actfilter = getFilter(req)
  
    # filter
    if actfilter!="":
        if actfilter in ("all", "*", t(lang(req),"admin_filter_all")):
            None # all users
        elif actfilter=="0-9":
            num = re.compile(r'([0-9])')
            if req.params.get("filtertype","")=="username":
                users = filter(lambda x: num.match(x.getName()), users)
            else:
                users = filter(lambda x: num.match(x.get("lastname")), users)
        elif actfilter=="else" or actfilter==t(lang(req),"admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            if req.params.get("filtertype","")=="username":
                users = filter(lambda x: not all.match(x.getName()), users)
            else:
                users = filter(lambda x: not all.match(x.get("lastname")), users)
        else:
            if req.params.get("filtertype","")=="username":
                users = filter(lambda x: x.getName().lower().startswith(actfilter), users)
            else:
                users = filter(lambda x: x.get("lastname").lower().startswith(actfilter), users)
            
    pages = Overview(req, users)

    # sorting
    if order != "":
        if int(order[0:1])==0:
            users.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))
        elif int(order[0:1])==1:
            users.sort(lambda x, y: cmp(x.getLastName().lower(),y.getLastName().lower()))
        elif int(order[0:1])==2:
            users.sort(lambda x, y: cmp(x.getFirstName().lower(),y.getFirstName().lower()))        
        elif int(order[0:1])==3:
            users.sort(lambda x, y: cmp(x.getEmail().lower(),y.getEmail().lower()))
        elif int(order[0:1])==4:
            users.sort(lambda x, y: cmp(x.getOrganisation(),y.getOrganisation()))    
        elif int(order[0:1])==5:
            users.sort(lambda x, y: cmp(x.getGroups(),y.getGroups()))
        elif int(order[0:1])==6:
            users.sort(lambda x, y: cmp(x.stdPassword(),y.stdPassword()))            
        if int(order[1:])==1:
            users.reverse()
    else:
        users.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))

    v = pages.getStdVars()
    v["filterattrs"] = [("username","admin_user_filter_username"),("lastname","admin_user_filter_lastname")]
    v["filterarg"] = req.params.get("filtertype", "username")
    v["sortcol"] = pages.OrderColHeader([t(lang(req),"admin_user_col_1"), t(lang(req),"admin_user_col_2"), t(lang(req),"admin_user_col_3"), t(lang(req),"admin_user_col_4"), t(lang(req),"admin_user_col_5"), t(lang(req),"admin_user_col_6"), t(lang(req),"admin_user_col_7")])
    v["options"] = list(useroption)
    v["users"] = users
    v["pages"] = pages
    v["usertype"] = usertype
    v["actfilter"] = actfilter
    v["auth"] = auth
    
    return req.getTAL("web/admin/modules/user.html", v, macro="view")

#
# edit/create user
#
def editUser_mask(req, id, err=0):
    global useroption
    ugroups = []
    
    usertype = req.params.get("usertype", "intern")
        
    if err==0 and id=="":
        # new user
        user = tree.Node("", type="user")
        user.setOption("c")
        
    elif err==0 and id!="":
        #edit user
        if usertype=="intern":
            user = getUser(id)
        else:
            user = getExternalUser(id)
    else:
        #error while filling values
        option = ""
        for key in req.params.keys():
            if key.startswith("option_"):
                option += key[7]

        for usergroup in req.params.get("usergroups","").split(";"):
            ugroups += [usergroup]
        
        user = tree.Node("", type="user")
        user.setName(req.params.get("username",""))
        user.setEmail(req.params.get("email",""))
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
    v["filtertype"] = req.params.get("filtertype","")
    v["actpage"] = req.params.get("actpage")
    return req.getTAL("web/admin/modules/user.html", v, macro="modify")
    
def sendmailUser_mask(req, id, err=0):

    v = getAdminStdVars(req)
    v["path"] = req.path[1:]
    
    if id=="execute" or id=="execu":

        userid = req.params["userid"]
        user = getUser(userid)
        if not user:
            path = req.path[1:].split("/")
            user = getExternalUser(userid, path[-1])

        password = makeRandomPassword()
        user.resetPassword(password)

        text = req.params["text"]
        text = text.replace("[wird eingesetzt]", password)
        try:
            mail.sendmail(req.params["from"],req.params["email"],req.params["subject"],text)
        except mail.SocketError:
            print "Socket error while sending mail"
            return req.getTAL("web/admin/modules/user.html", v, macro="sendmailerror")
        return req.getTAL("web/admin/modules/user.html", v, macro="sendmaildone")

    user = getUser(id)
    if not user:
        path = req.path[1:].split("/")
        user = getExternalUser(id, path[-1])
    
    x = {}
    x["name"] = user.getName()
    x["host"] = config.get("host.name")
    x["login"] = user.getName()
    x["isEditor"] = user.isEditor()
    x["collections"] = list()
    x["groups"] = user.getGroups()
    x["language"] = lang(req)


    access = acl.AccessData(user=user)
    for node in tree.getRoot("collections").getChildren():
        if access.hasReadAccess(node):
            if access.hasWriteAccess(node):
                x["collections"].append(node.name+" (lesen/schreiben)")
            else:
                x["collections"].append(node.name+" (nur lesen)")


    v["mailtext"] = req.getTAL("web/admin/modules/user.html", x, macro="emailtext").strip()
    v["email"] = user.getEmail()
    v["userid"] = user.getName()

    return req.getTAL("web/admin/modules/user.html", v, macro="sendmail")

