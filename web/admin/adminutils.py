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
import logging
import os
import math
import sys
import traceback

import core.users as users
import core.config as config
from utils.utils import Link, splitpath, parseMenuString
from core.translation import t, lang
from core.tree import getRoot
from core.transition import httpstatus
from utils.strings import ensure_unicode_returned


logg = logging.getLogger(__name__)


def getAdminStdVars(req):
    page = ""
    if req.params.get("page", "") == "0":
        page = "?page=0"

    user = users.getUserFromRequest(req)

    tabs = [("0-9", "09")]
    for i in range(65, 91):
        tabs.append((unichr(i), unichr(i)))
    tabs.append(("admin_filter_else", "-"))
    tabs.append(("admin_filter_all", "*"))

    actpage = req.params.get("page", req.params.get("actpage", "1"))
    return {"user": user, "page": page, "op": req.params.get(
        "op", ""), "tabs": tabs, "actpage": actpage, "actfilter": req.params.get("actfilter", "")}


class Overview:

    def __init__(self, req, list):
        self.req = req
        self.path = req.path[1:]
        self.language = lang(req)
        self.stdVars = getAdminStdVars(self.req)

        # self.page = 0 or None -> all entries
        try:
            self.page = int(req.params.get("page", req.params.get("actpage", 1)))
        except ValueError:
            self.page = req.params.get("actpage")

        if "firstpage" in req.params.keys():
            self.page = 1
        elif "resetpage" in req.params.keys():
            self.page = 0
        max_page = len(list) / int(config.settings["admin.pageitems"])
        if max_page + 1 < self.page:
            self.page = 1
            req.params["page"] = 1

        if self.page == 0:
            self.start = 0
            self.end = len(list)
        else:
            self.start = (self.page - 1) * int(config.settings["admin.pageitems"])
            self.end = self.start + int(config.settings["admin.pageitems"])
        self.list = list

    def getStdVars(self):
        return self.stdVars

    def getStart(self):
        return int(self.start)

    def getEnd(self):
        return int(self.end)

    def getNoPages(self):
        return int(math.ceil(float(len(self.list)) / float(config.settings["admin.pageitems"])))

    def printPageList(self):
        order = self.req.params.get("order", "")
        ret = ''
        if self.page > 0:
            for p in range(1, self.getNoPages() + 1):
                b_class = "admin_page"
                if p == self.page:
                    b_class = "admin_page_act"
                ret += '<button type="submit" name="page" class="' + b_class + '" title="' + \
                    t(self.language, "admin_page") + ' ' + ustr(p) + '" value="' + ustr(p) + '">' + ustr(p) + '</button> '
        if len(ret) == 0:
            return ""
        return '[' + ret + '] '

    def printPageAll(self):
        if self.page != 0:
            return '<button name="resetpage" title="' + \
                t(self.language,
                  "admin_allelements_title") + '" class="admin_page" type="submit" value="">' + t(self.language,
                                                                                                  "admin_allelements") + '</button>'
        else:
            return '<button name="firstpage" title="' + \
                t(self.language,
                  "admin_pageelements_title") + '" class="admin_page" type="submit" value="">' + t(self.language,
                                                                                                   "admin_pageelements_title") + '</button>'

    def OrderColHeader(self, cols, order="", addparams=""):
        order = self.req.params.get("order", "")
        ordercol = 0
        orderdir = 0
        retList = []

        if order != "":
            ordercol = int(order[0:1])
            orderdir = int(order[1:])
        i = 0
        for col in cols:
            if col != "":
                if i == ordercol:
                    if orderdir == 0:
                        retList += [Link(ustr(i) + "1", t(self.language, "admin_sort_label"), col + ' <img src="/img/az.png" border="0" />')]
                    else:
                        retList += [Link(ustr(i) + "0", t(self.language, "admin_sort_label"), col + ' <img src="/img/za.png" border="0" />')]
                else:
                    retList += [Link(ustr(i) + "0", t(self.language, "admin_sort_label"), col)]
            i += 1
        return retList

""" evaluate current filter """


def getFilter(req):
    actfilter = req.params.get("actfilter", req.params.get("filter", "all")).lower()
    if "filterbutton" in req.params.keys():
        actfilter = req.params.get("filterbutton").lower()

    if len(actfilter) > 20:
        return "all"
    return actfilter

""" fills variable for sort column """


def getSortCol(req):
    order = req.params.get("order", "")
    for key in req.params.keys():
        if key.startswith("sortcol_"):
            order = key[8:]
            req.params["order"] = order
    return order

""" load module for admin area """


def findmodule(type):
    if type in adminModules:
        return adminModules[type]

    try:
        m = __import__("web.admin.modules." + type)
        m = eval("m.admin.modules." + type)
    except:
        logg.exception("Warning: couldn't load module for type %s", type)
        m = __import__("web.admin.modules.default")
        m = eval("m.admin.modules.default")
    return m

""" main method for content area """

@ensure_unicode_returned(name="adminutils.show_content")
def show_content(req, op):
    user = users.getUserFromRequest(req)

    if not user.inGroup(config.get('user.admingroup')):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/admin/frame.html", {}, macro="errormessage")
    else:
        if op == "" or op not in getRoot().get("admin.menu"):
            op = "menumain"
        module = findmodule(op.split("_")[0])

        if op.find("_") > -1:
            return module.spc(req, op)
        else:
            return module.validate(req, op)

# delivers all admin modules


def getAdminModules(path):
    mods = {}
    for root, dirs, files in path:
        for name in [f for f in files if f.endswith(".py") and f != "__init__.py"]:
            m = __import__("web.admin.modules." + name[:-3])
            m = eval("m.admin.modules." + name[:-3])
            mods[name[:-3]] = m

    # test for external modules by plugin
    for k, v in config.getsubset("plugins").items():
        path, module = splitpath(v)
        try:
            sys.path += [path + ".adminmodules"]

            for root, dirs, files in os.walk(os.path.join(config.basedir, v + "/adminmodules")):
                for name in [f for f in files if f.endswith(".py") and f != "__init__.py"]:
                    m = __import__(module + ".adminmodules." + name[:-3])
                    m = eval("m.adminmodules." + name[:-3])
                    mods[name[:-3]] = m
        except ImportError:
            pass  # no admin modules in plugin
    return mods

# delivers all active admin modules in navigations
adminModules = {}


def adminNavigation():
    if len(adminModules) == 0:
        # load admin modules
        mods = getAdminModules(os.walk(os.path.join(config.basedir, 'web/admin/modules')))
        for mod in mods:
            if hasattr(mods[mod], "getInformation"):
                adminModules[mod] = (mods[mod])

    # get module configuration
    root = getRoot()
    admin_configuration = root.get("admin.menu")

    if admin_configuration == "":
        # no confguration found -> use default
        admin_configuration = "menumain();menuuser(usergroup;user);menuacl(acls);menudata(metatype;mapping);menuworkflow(workflows);menusystem(logfile;flush;settings;settingsmenu)"
        root.set("admin.menu", admin_configuration)

    return parseMenuString(admin_configuration[:-1])


def getAdminModulesVisible():
    ret = []
    for menu in adminNavigation():
        ret.append(menu.getId())
        for item in menu.getItemList():
            ret.append(item)
    return ret


def getAdminModuleInformation(mod, key=""):
    if mod in adminModules.keys():
        m = adminModules[mod]
        if hasattr(m, "getInformation"):
            info = m.getInformation()
            if key not in info.keys():
                return info
            else:
                return info[key]


def getMenuItemID(menulist, path):
    if path == "":
        return ["admin_menu_menumain"]

    p = path.split('/')
    for item in menulist:
        for subitem in item.getItemList():
            if subitem[1].endswith(p[0]):
                return [item.name, "admin_menu_" + subitem[0]]

    return ["admin_menu_menumain"]
