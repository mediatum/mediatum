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
import core.tree as tree
import core.athana as athana
import logging
import core.usergroups as usergroups

from web.admin.adminutils import Overview, getAdminStdVars
from core.usergroups import groupoption, loadGroupsFromDB, getGroup, existGroup, create_group, createAcRule, deleteGroup, getNumUsers
from core.translation import t, lang


#
# standard validator
#
def validate(req, op):
    try:
        for key in req.params.keys():
            if key.startswith("new"):
                # create new group
                return editGroup_mask(req, "")

            elif key.startswith("edit_"):
                # edit usergroup
                return editGroup_mask(req, str(key[5:-2]))

            elif key.startswith("delete_"):
                # delete group
                deleteGroup(key[7:-2])
                break

            elif key == "form_op":
                _option =""
                for key in req.params.keys():
                    if key.startswith("option_"):
                        _option += key[7]
                            
                if req.params["form_op"] == "save_new":
                    # save new group values
                    if str(req.params["groupname"])=="":
                        return editGroup_mask(req, "", 1) # no groupname selected
                    elif existGroup(req.params["groupname"]):
                        return editGroup_mask(req, "", 2) # group still existing
                    else:
                        if req.params.get("create_rule","")=="True":
                            createAcRule(req.params["groupname"])
                        create_group(req.params["groupname"], req.params["description"], str(_option))
                    break
                elif req.params["form_op"] == "save_edit":
                    # save changed values
                    groupname = req.params["groupname"]
                    group = getGroup(groupname)
                    group.setDescription(req.params["description"])
                    group.setOption(str(_option))

        return view(req)

    except:
        print "Warning: couldn't load module for type",type
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])

def view(req):

    global groupoption
    groups = list(loadGroupsFromDB())
    pages = Overview(req, groups)
    order = req.params.get("order","")

    # sorting
    if order != "":
        if int(order[0:1])==0:
            groups.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower())) 
        elif int(order[0:1])==1:
            groups.sort(lambda x, y: cmp(getNumUsers(x.getName()),getNumUsers(y.getName())))        
        if int(order[1:])==1:
            groups.reverse()
    else:
        groups.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower())) 

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req), "admin_usergroup_col_1"), t(lang(req), "admin_usergroup_col_2")])
    v["options"] = list(groupoption)
    v["groups"] = groups
    v["pages"] = pages
    return req.getTAL("/web/admin/modules/usergroup.html", v, macro="view")

#
# edit/create usergroup
#
def editGroup_mask(req, id, err=0):
    global groupoption
       
    if err==0 and id=="":
        # new usergroup
        group = tree.Node("", type="usergroup")
        
    elif id!="":
        #edit usergroup
        group = getGroup(id)

    else:
        #error while filling values
        option = ""
        for key in req.params.keys():
            if key.startswith("option_"):
                option += key[7]

        group = tree.Node("", type="usergroup")
        group.setName(req.params.get("groupname",""))
        group.setDescription(req.params.get("description",""))
        group.setOption(option)

    v = getAdminStdVars(req)
    v["error"] = err
    v["group"] = group
    v["groupoption"] = groupoption
    return req.getTAL("/web/admin/modules/usergroup.html", v, macro="modify")
    
