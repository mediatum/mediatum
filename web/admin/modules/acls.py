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
import core.acl as acl
import re

from core.users import loadUsersFromDB
from core.usergroups import loadGroupsFromDB
from core.acl import AccessRule
from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from core.translation import t, lang



def validate(req, op):
    try:
        for key in req.params.keys():
            if key == "style" and req.params.get("style","")=="editor":
                return showEditor(req)

            if key.startswith("new"):
                # create new rule
                return editRule_mask(req, "")

            elif key.startswith("edit_"):
                # edit rule
                return editRule_mask(req, str(key[key.index("_")+1:-2]))

            elif key.startswith("delete_"):
                # delete rule
                acl.deleteRule(str(key[7:-2]))
                break
                
            elif key.startswith("reset_"):
                # remove not defined rule names from nodes
                acl.resetNodeRule(key[6:-2])
                break
                
            elif key == "form_op":
                if req.params["form_op"] == "save_new":
                    # save rule values
                    if str(req.params["rulename"])=="" or req.params["rule"]=="":
                        return editRule_mask(req, "", 1) # no rulename or rulestring

                    elif acl.existRule(req.params["rulename"]):
                        return editRule_mask(req, "", 2) # rule still existing
                    else:
                        acl.addRule(AccessRule(str(req.params["rulename"]), str(req.params["rule"]), str(req.params["description"])))
                    break
                elif req.params["form_op"] == "save_edit":
                    # update rule

                    if req.params["rule"] != "":
                        acl.updateRule(AccessRule(str(req.params["rulename"]), str(req.params["rule"]), str(req.params["description"])) )
                    break
        return view(req)

    except:
        print "Warning: couldn't load module for type",type
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])


#
# show all defindes acl-rules
#
def view(req):
    global useroption
    rules = acl.getRuleList()
 
    actfilter = getFilter(req)
    order = getSortCol(req)
    
    # filter
    if actfilter!="":
        if actfilter=="all" or actfilter==t(lang(req),"admin_filter_all"):
            None # all users
        elif actfilter=="0-9":
            num = re.compile(r'([0-9])')
            rules = filter(lambda x: num.match(x.getName()), rules)
        elif actfilter=="else" or actfilter==t(lang(req),"admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            rules = filter(lambda x: not all.match(x.getName()), rules)
        else:
            rules = filter(lambda x: x.getName().lower().startswith(actfilter), rules)
    
    pages = Overview(req, rules)
    
    # sorting
    if order != "":
        if int(order[0:1])==0:
            rules.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))
        elif int(order[0:1])==1:
            rules.sort(lambda x, y: cmp(x.rulestr,y.rulestr))
        elif int(order[0:1])==2:
            rules.sort(lambda x, y: cmp(x.description,y.description))            
        if int(order[1:])==1:
            rules.reverse()
    else:
        rules.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req),"admin_acl_col_1"), t(lang(req),"admin_acl_col_2"), t(lang(req),"admin_acl_col_3")])
    v["rules"] = rules
    v["pages"] = pages
    v["missing_rules"] = acl.getMissingRuleNames()
    v["actfilter"] = actfilter
    return req.getTAL("web/admin/modules/acls.html", v, macro="view")

#
# edit rule
#
def editRule_mask(req, id, err=0):

    if err==0 and id=="":
        # new rule
        rule = AccessRule("", "( true )", "")

    elif id!="" and err==0:
        # edit rule
        rule = acl.getRule(id)
 
    else:
        # error
        rule = AccessRule(req.params["rulename"], req.params["rule"], req.params["description"])

    v = getAdminStdVars(req)
    v["error"] = err
    v["rule"] = rule
    return req.getTAL("web/admin/modules/acls.html", v, macro="modify")

#
# open ACL-Editor
#
def showEditor(req):
    v = {}
    usersel="""\"<table border=\\"0\\"><tr><td valign=\\"top\\">"""+t(lang(req),"admin_acl_editor_user")+""":</td><td><select name=\\"users\\" id=\\"users\\" size=\\"4\\" onclick=\\"setValue(this)\\">"""
    for user in loadUsersFromDB():
        usersel += """<option value=\\\"""" + user.getName() + """\\\">""" + user.getName() + """</option>"""
    usersel += """</tr></table>\""""
    v["userstr"] = usersel

    groupsel="""\"<table border=\\"0\\"><tr><td valign=\\"top\\">"""+t(lang(req),"admin_acl_editor_group")+""":</td><td><select name=\\"users\\" id=\\"users\\" size=\\"4\\" ONCLICK=setValue(this)>"""
    for group in loadGroupsFromDB():
        groupsel += """<option value=\\\"""" + group.getName() + """\\\">""" + group.getName() + """</option>"""
    groupsel += """</tr></table>\""""
    v["groupstr"] = groupsel

    v["datestr"] = """\"<table border=\\"0\\"><tr><td rowspan=\\"2\\" valign=\\"top\\">"""+t(lang(req),"admin_acl_editor_operator")+""":</td><td rowspan=\\"2\\"><select name=\\"ruleop\\" id=\\"ruleop\\" size=\\"4\\" ONCLICK=setValue(this) ><option value=\\"<= \\">&lt=</option><option value=\\">= \\">&gt=</option><option value=\\"< \\">&lt</option><option value=\\"> \\">&gt</option></select></td><td valign=\\"top\\">"""+t(lang(req),"admin_acl_editor_date")+""":</td><td><input type=\\"text\\" name=\\"date\\" id=\\"datevalue\\" size=\\"10\\" maxlength=\\"10\\"><button name=\\"dateselect\\" type=\\"button\\" ONCLICK=setValue(this)>"""+t(lang(req),"admin_acl_editor_buttonok")+"""</button></td>    </tr><tr><td align=\\"right\\" colspan=\\"2\\"><small>"""+t(lang(req),"admin_acl_editor_format")+""": dd.mm.yyyy</small></td></tr></table>\""""
    v["ipstr"] = """\"<table border=\\"0\\"><tr><td valign=\\"top\\">"""+t(lang(req),"admin_acl_editor_ip")+""":</td><td><input type=\\"text\\" name=\\"ipvalue\\" id=\\"ipvalue\\" size=\\"15\\"><button name=\\"ipselect\\" type=\\"button\\" ONCLICK=setValue(this)>"""+t(lang(req),"admin_acl_editor_buttonok")+"""</button></td></tr><tr><td align=\\"right\\" colspan=\\"2\\"><small>"""+t(lang(req),"admin_acl_editor_format")+""": xxx.xxx.xxx.xxx</small></td></tr></table>\""""
   
    return req.getTAL("web/admin/modules/acls.html", v, macro="acleditor")

    
