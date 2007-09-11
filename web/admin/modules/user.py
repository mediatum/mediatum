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

from core.usergroups import loadGroupsFromDB
from core.users import loadUsersFromDB, useroption, getUser, update_user, existUser, create_user, makeRandomPassword, deleteUser

from web.admin.adminutils import Overview, getAdminStdVars
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
                return editUser_mask(req, str(key[key.index("_")+1:-2]))

            elif key.startswith("sendmail_") and req.params.get("form_op","")!="cancel":
                # edit user
                return sendmailUser_mask(req, str(key[key.index("_")+1:-2]))

            elif key.startswith("delete_"):
                # delete user
                deleteUser(getUser(key[7:-2]))
                break

            elif key.startswith("reset_"):
                # reset password
                if req.params["change_passwd"]!="":
                    getUser(key[6:-2]).resetPassword(req.params["change_passwd"])
                else:
                    getUser(key[6:-2]).resetPassword(config.settings["user.passwd"])
                break

            elif key == "form_op":
                _option =""
                for key in req.params.keys():
                    if key.startswith("option_"):
                        _option += key[7]
                            
                if req.params["form_op"] == "save_new":
                    # save user values

                    try: grp = req.params["usergroups"]
                    except KeyError: grp = ""

                    if str(req.params["username"])=="" or grp=="" or str(req.params["email"])=="":
                        return editUser_mask(req, "", 1) # no username or group selected
                    elif existUser(req.params["username"]):
                        return editUser_mask(req, "", 2) #user still existing
                    else:
                        create_user(req.params["username"], email=req.params["email"], groups=req.params["usergroups"].replace(";", ","), option=_option)
                    break
                elif req.params["form_op"] == "save_edit":
                    # update user

                    if str(req.params["email"])=="":
                        return editUser_mask(req, req.params["username"], 1) # no username or group selected
                    else:
                        update_user(req.params["username"], email=req.params["email"], groups=req.params["usergroups"].replace(";", ","), option=_option, new_name=req.params["username_new"])
                    break

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
    users = list(loadUsersFromDB())
    pages = Overview(req, users)
    order = req.params.get("order","")

    # sorting
    if order != "":
        if int(order[0:1])==0:
            users.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))
        elif int(order[0:1])==1:
            users.sort(lambda x, y: cmp(x.getEmail().lower(),y.getEmail().lower()))
        elif int(order[0:1])==2:
            users.sort(lambda x, y: cmp(x.getGroups(),y.getGroups()))
        elif int(order[0:1])==3:
            users.sort(lambda x, y: cmp(x.stdPassword(),y.stdPassword()))            
        if int(order[1:])==1:
            users.reverse()
    else:
        users.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))
    
    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req),"admin_user_col_1"), t(lang(req),"admin_user_col_2"), t(lang(req),"admin_user_col_3"), t(lang(req),"admin_user_col_4")])
    v["options"] = list(useroption)
    v["users"] = users
    v["pages"] = pages
    return req.getTAL("web/admin/modules/user.html", v, macro="view")

#
# edit/create user
#
def editUser_mask(req, id, err=0):
    global useroption
    ugroups = []
        
    if err==0 and id=="":
        # new user
        user = tree.Node("", type="user")
        user.setOption("c")
        
    elif id!="":
        #edit user
        user = getUser(id)

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

    v = getAdminStdVars(req)
    v["error"] = err
    v["user"] = user
    v["groups"] = loadGroupsFromDB()
    v["ugroups"] = ugroups
    v["useroption"] = useroption
    v["id"] = id
    return req.getTAL("web/admin/modules/user.html", v, macro="modify")
    
def sendmailUser_mask(req, id, err=0):

    v = getAdminStdVars(req)
    
    if id == "execute" or id == "execu":

        userid = req.params["userid"]
        user = getUser(userid)
        password = makeRandomPassword()
        user.resetPassword(password)

        text = req.params["text"]
        text = text.replace("[wird eingesetzt]", password)
        mail.sendmail(req.params["from"],req.params["email"],req.params["subject"],text)
        return req.getTAL("web/admin/modules/user.html", v, macro="sendmaildone")

    user = getUser(id)
    
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

