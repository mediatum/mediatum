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
import re
import os

from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from core.usergroups import groupoption, loadGroupsFromDB, getGroup, existGroup, create_group, createAcRule, deleteGroup, getNumUsers
from core.translation import t, lang


#
# standard validator
#
def validate(req, op):
    print req.params
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

        if "form_op" in req.params.keys():     
            _option =""
            for key in req.params.keys():
                if key.startswith("option_"):
                    _option += key[7]
                            
            if req.params.get("form_op","")=="save_new":
                # save new group values
                if req.params.get("groupname","")=="":
                    return editGroup_mask(req, "", 1) # no groupname selected
                elif existGroup(req.params.get("groupname","")):
                    return editGroup_mask(req, "", 2) # group still existing
                else:
                    if req.params.get("create_rule","")=="True":
                        createAcRule(req.params.get("groupname",""))
                    group = create_group(req.params.get("groupname",""), req.params.get("description",""), str(_option))
                    group.setHideEdit(req.params.get("leftmodule","").strip())

            elif req.params.get("form_op")=="save_edit":
                # save changed values
                groupname = req.params.get("groupname","")
                group = getGroup(groupname)
                group.setDescription(req.params.get("description",""))
                group.setOption(str(_option))
                group.setHideEdit(req.params.get("leftmodule","").strip())

        return view(req)

    except:
        print "Warning: couldn't load module for type",type
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])

def view(req):

    global groupoption
    groups = list(loadGroupsFromDB())   
    order = getSortCol(req)
    actfilter = getFilter(req)
    
    # filter
    if actfilter!="":
        if actfilter=="all" or actfilter==t(lang(req),"admin_filter_all"):
            None # all groups
        elif actfilter=="0-9":
            num = re.compile(r'([0-9])')
            groups = filter(lambda x: num.match(x.getName()), groups)
        elif actfilter=="else" or actfilter==t(lang(req),"admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            groups = filter(lambda x: not all.match(x.getName()), groups)
        else:
            groups = filter(lambda x: x.getName().lower().startswith(actfilter), groups)

    pages = Overview(req, groups)
       
    # sorting
    if order != "":
        if int(order[0:1])==0:
            groups.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower())) 
        elif int(order[0:1])==1:
            groups.sort(lambda x, y: cmp(getNumUsers(x.getName()),getNumUsers(y.getName())))  
        elif int(order[0:1])==2:
            gl = {}
            for g in groups:
                gl[g.id] = g.getSchemas()
            groups.sort(lambda x, y: cmp(len(gl[x.id]),len(gl[y.id])))
        elif int(order[0:1])==3:
            groups.sort(lambda x, y: cmp(x.getHideEdit()=="",y.getHideEdit()=="")) 
            
        if int(order[1:])==1:
            groups.reverse()
    else:
        groups.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower())) 

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req), "admin_usergroup_col_1"), t(lang(req), "admin_usergroup_col_2"), t(lang(req), "admin_usergroup_col_3"), t(lang(req), "admin_usergroup_col_4")])
    v["options"] = list(groupoption)
    v["groups"] = groups
    v["pages"] = pages
    v["actfilter"] = actfilter
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
        group.setHideEdit(req.params.get("leftmodule","").split(';'))
        group.setOption(option)

    v = getAdminStdVars(req)
    v["error"] = err
    v["group"] = group
    v["groupoption"] = groupoption
    v["modulenames"] = getEditModuleNames()
    v["val_left"] = buildRawModuleLeft(group, lang(req))
    v["val_right"] = buildRawModuleRight(group, lang(req))
    v["emails"] = ', '.join([u.get('email') for u in group.getChildren()])
    return req.getTAL("/web/admin/modules/usergroup.html", v, macro="modify")
    

def getEditModuleNames():
    ret = []
    for root, dirs, files in os.walk('web/edit'):
        for f in files:
            if f.startswith("edit_") and f[-3:]==".py" and not f.startswith("edit_common"):
                ret.append(f[5:-3])
    return ret
    
def buildRawModuleLeft(group, language):
    ret = ""
    if group.getHideEdit()=="":
        return ret
    for hide in group.getHideEdit().split(';'):
        ret += '<option value="'+hide+'">'+t(language,'e_'+hide,)+'</option>'
    return ret
    
def buildRawModuleRight(group, language):
    ret = ""
    hide = group.getHideEdit().split(';')
    for mod in getEditModuleNames():
        if mod not in hide:
            ret += '<option value="'+mod+'">'+t(language,'e_'+mod,)+'</option>'
    return ret
