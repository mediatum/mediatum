"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Peter Heckl <heckl@ub.tum.de>

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
import core.tree as tree
import logging
import core.users as users
import core.config as config
import re
import os

from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from core.usergroups import (loadGroupsFromDB, groupoption, getGroup, existGroup, create_group, updateAclRule,
                             deleteGroup, getNumUsers, getMetadata, saveGroupMetadata, sortUserGroups)
from core.translation import t, lang
from utils.utils import splitpath, u


def getInformation():
    return{"version": "1.0"}

logg = logging.getLogger(__name__)
ALLOW_DYNAMIC_USERS = False


def validate(req, op):
    """standard validator"""
    user = users.getUserFromRequest(req)

    try:

        if "action" in req.params.keys():
            if req.params.get("action") == "titleinfo":
                group = getGroup(u(req.params.get("group")))
                schema = group.getSchemas()
                req.write('|'.join(schema))
            return ""

        for key in req.params.keys():
            if key.startswith("new"):
                # create new group
                return editGroup_mask(req, "")

            elif key.startswith("edit_"):
                # edit usergroup
                return editGroup_mask(req, key[5:-2])

            elif key.startswith("delete_"):
                # delete group
                logg.debug("user %r going to delete group %r", user.getName(), key[7:-2])
                deleteGroup(key[7:-2])
                break

        if "form_op" in req.params.keys():
            _option = ""
            for key in req.params.keys():
                if key.startswith("option_"):
                    _option += key[7]

            if req.params.get("form_op", "") == "save_new":
                # save new group values
                if req.params.get("groupname", "") == "":
                    return editGroup_mask(req, "", 1)  # no groupname selected
                elif existGroup(req.params.get("groupname", "")):
                    return editGroup_mask(req, "", 2)  # group still existing
                else:
                    logg.debug("user %r going to save new group %r", user.getName(), req.params.get("groupname", ""))
                    if req.params.get("create_rule", "") == "True":
                        updateAclRule(req.params.get("groupname", ""), req.params.get("groupname", ""))
                    if req.params.get("checkbox_allow_dynamic", "") in ["on", "1"]:
                        allow_dynamic = "1"
                    else:
                        allow_dynamic = ""
                    dynamic_users = req.params.get("dynamic_users", "")
                    group = create_group(req.params.get("groupname", ""),
                                         description=req.params.get("description", ""),
                                         option=ustr(_option),
                                         allow_dynamic=allow_dynamic,
                                         dynamic_users=dynamic_users,
                                         )
                    group.setHideEdit(req.params.get("leftmodule", "").strip())
                    saveGroupMetadata(group.name, req.params.get("leftmodulemeta", "").strip())

            elif req.params.get("form_op") == "save_edit":
                # save changed values
                groupname = req.params.get("groupname", "")
                oldgroupname = req.params.get("oldgroupname", "")
                group = getGroup(oldgroupname)
                if oldgroupname != groupname:
                    updateAclRule(oldgroupname, groupname)
                group.setName(groupname)
                group.setDescription(req.params.get("description", ""))
                group.setOption(ustr(_option))
                group.setHideEdit(req.params.get("leftmodule", "").strip())
                saveGroupMetadata(groupname, req.params.get("leftmodulemeta", "").split(";"))

                if ALLOW_DYNAMIC_USERS:
                    allow_dynamic = req.params.get("checkbox_allow_dynamic", "")
                    dynamic_users = req.params.get("dynamic_users", "")
                    if allow_dynamic.lower() in ['on', 'true', '1']:
                        group.set("allow_dynamic", "1")
                    else:
                        group.set("allow_dynamic", "")
                    group.set("dynamic_users", dynamic_users)
                if groupname == oldgroupname:
                    logg.debug("user %r edited group %r", user.getName(), groupname)
                else:
                    logg.debug("user %r edited group %r, new groupname: %r", user.getName(), oldgroupname, groupname)
            sortUserGroups()
        return view(req)

    except:
        logg.exception("exception in validate")


def view(req):
    groups = list(loadGroupsFromDB())
    order = getSortCol(req)
    actfilter = getFilter(req)

    # filter
    if actfilter != "":
        if actfilter in("all", t(lang(req), "admin_filter_all"), "*"):
            None  # all groups
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            groups = filter(lambda x: num.match(x.getName()), groups)
        elif actfilter == "else" or actfilter == t(lang(req), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            groups = filter(lambda x: not all.match(x.getName()), groups)
        else:
            groups = filter(lambda x: x.getName().lower().startswith(actfilter), groups)

    pages = Overview(req, groups)

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            groups.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))
        elif int(order[0:1]) == 1:
            groups.sort(lambda x, y: cmp(getNumUsers(x.getName()), getNumUsers(y.getName())))
        elif int(order[0:1]) == 2:
            gl = {}
            for g in groups:
                gl[g.id] = g.getSchemas()
            groups.sort(lambda x, y: cmp(len(gl[x.id]), len(gl[y.id])))
        elif int(order[0:1]) == 3:
            groups.sort(lambda x, y: cmp(x.getHideEdit() == "", y.getHideEdit() == ""))

        if int(order[1:]) == 1:
            groups.reverse()
    # else:
    #    groups.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req), "admin_usergroup_col_1"), t(lang(req), "admin_usergroup_col_2"), t(
        lang(req), "admin_usergroup_col_3"), t(lang(req), "admin_usergroup_col_4")])
    v["options"] = list(groupoption)
    v["groups"] = groups
    v["pages"] = pages
    v["actfilter"] = actfilter
    return req.getTAL("/web/admin/modules/usergroup.html", v, macro="view")


def editGroup_mask(req, id, err=0):
    """edit/create usergroup"""
    newusergroup = 0
    if err == 0 and id == "":
        # new usergroup
        group = tree.Node("", type="usergroup")
        newusergroup = 1
    elif id != "":
        # edit usergroup
        group = getGroup(id)

    else:
        # error while filling values
        option = ""
        for key in req.params.keys():
            if key.startswith("option_"):
                option += key[7]

        group = tree.Node("", type="usergroup")
        group.setName(req.params.get("groupname", ""))
        group.setDescription(req.params.get("description", ""))
        group.setHideEdit(req.params.get("leftmodule", "").split(';'))

        group.setOption(option)

    v = getAdminStdVars(req)
    v["error"] = err
    v["group"] = group
    v["groupoption"] = groupoption
    v["modulenames"] = getEditModuleNames()
    v["val_left"] = buildRawModuleLeft(group, lang(req))
    v["val_right"] = buildRawModuleRight(group, lang(req))
    v["valmeta_left"] = buildRawModuleMetaLeft(group)
    v["valmeta_right"] = buildRawModuleMetaRight(group)
    v["emails"] = ', '.join([u.get('email') for u in group.getChildren()])
    v["actpage"] = req.params.get("actpage")
    v["newusergroup"] = newusergroup

    v["allow_dynamic_users"] = ALLOW_DYNAMIC_USERS  # global flag
    v["allow_dynamic"] = group.get("allow_dynamic")  # for checkbox
    v["dynamic_users"] = group.get("dynamic_users")

    return req.getTAL("/web/admin/modules/usergroup.html", v, macro="modify")


def getEditModuleNames():
    ret = []
    path = os.walk(os.path.join(config.basedir, 'web/edit/modules'))
    for root, dirs, files in path:
        for name in [f for f in files if f.endswith(".py") and f != "__init__.py"]:
            ret.append(name[:-3])

    # test for external modules by plugin
    for k, v in config.getsubset("plugins").items():
        path, module = splitpath(v)
        try:
            sys.path += [path + ".editmodules"]

            for root, dirs, files in os.walk(os.path.join(config.basedir, v + "/editmodules")):
                for name in [f for f in files if f.endswith(".py") and f != "__init__.py"]:
                    ret.append(name[:-3])
        except ImportError:
            pass  # no edit modules in plugin
    return ret


def buildRawModuleLeft(group, language):
    ret = ""
    if group.getHideEdit() == "":
        return ret
    hidelist = group.getHideEdit().split(';')
    hidelist.sort(lambda x, y: cmp(t(language, 'e_' + x), t(language, 'e_' + y)))
    for hide in hidelist:
        ret += '<option value="%s">%s</option>' % (hide, t(language, 'e_' + hide, ))

    return ret


def buildRawModuleRight(group, language):
    ret = ""
    hide = group.getHideEdit().split(';')
    modulenames = getEditModuleNames()
    modulenames.sort(lambda x, y: cmp(t(language, 'e_' + x).lower(), t(language, 'e_' + y).lower()))
    for mod in modulenames:
        if mod not in hide:
            ret += '<option value="%s">%s</option>' % (mod, t(language, 'e_' + mod, ))
    return ret


def buildRawModuleMetaLeft(group):
    ret = ""
    metadatanames = getMetadata(group)
    metadatanames.sort(lambda x, y: cmp(x.lower(), y.lower()))
    for met in metadatanames:
        ret += '<option value="%s">%s</option>' % (met, met)
    return ret


def buildRawModuleMetaRight(group):
    ret = ""
    mdts = [mdt.name for mdt in tree.getRoot("metadatatypes").getChildren()]
    mdts.sort(lambda x, y: cmp(x.lower(), y.lower()))
    assignedList = getMetadata(group)
    for mod in mdts:
        if mod not in assignedList:
            ret += '<option value="%s">%s</option>' % (mod, mod)
    return ret
