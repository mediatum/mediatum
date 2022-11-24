# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os
import math
import sys
import flask as _flask

import mediatumtal.tal as _tal

import core.config as config
import core.translation as _core_translation
import core.users as users
from core import db
from core import httpstatus
from core.database.postgres.user import AuthenticatorInfo
from core.database.postgres.user import User
from core.systemtypes import Root
from utils.strings import ensure_unicode_returned
from utils.utils import get_menu_strings
from utils.utils import Link
from utils.utils import parse_menu_struct
from core.exceptions import SecurityException
from .modules import default as _modules_default
from .modules import mapping as _modules_mapping
from .modules import memstats as _modules_memstats
from .modules import menusystem as _modules_menusystem
from .modules import menuworkflow as _modules_menuworkflow
from .modules import menudata as _modules_menudata
from .modules import menuacl as _modules_menuacl
from .modules import menumain as _modules_menumain
from .modules import menuuser as _modules_menuuser
from .modules import metatype as _modules_metatype
from .modules import workflows as _modules_workflows

logg = logging.getLogger(__name__)
q = db.query

_menu = (
    "menumain",
    { "menudata": (
        "metatype",
        "mapping",
        )},
    { "menuworkflow": (
        "workflows",
        )},
)

# delivers all active admin modules in navigations
adminModules = {m.__name__.replace("web.admin.modules.", ""):m for m in (
    _modules_default,
    _modules_memstats,
    _modules_menusystem,
    _modules_metatype,
    _modules_menuworkflow,
    _modules_mapping,
    _modules_menudata,
    _modules_menuacl,
    _modules_menuuser,
    _modules_workflows,
    _modules_menumain,
    )}


def getAdminStdVars(req):
    page = ""
    if req.params.get("page", "") == "0":
        page = "?page=0"

    user = users.user_from_session()

    tabs = [("0-9", "09")]
    for i in range(65, 91):
        tabs.append((unichr(i), unichr(i)))
    tabs.append(("admin_filter_else", "-"))
    tabs.append(("all", "*"))

    actpage = req.params.get("page", req.params.get("actpage", "1"))
    return {"user": user, "page": page, "op": req.params.get(
        "op", ""), "tabs": tabs, "actpage": actpage, "actfilter": req.params.get("actfilter", "")}


class Overview:

    def __init__(self, req, list):
        self.req = req
        self.path = req.mediatum_contextfree_path[1:]
        self.language = _core_translation.set_language(req.accept_languages)
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
            
        items_per_page = config.getint("admin.pageitems", 20)
            
        max_page = len(list) // items_per_page
        if max_page + 1 < self.page:
            self.page = 1
            req.params["page"] = 1

        if self.page == 0:
            self.start = 0
            self.end = len(list)
        else:
            self.start = (self.page - 1) * items_per_page
            self.end = self.start + items_per_page
        self.list = list

    def getStdVars(self):
        return self.stdVars

    def getStart(self):
        return int(self.start)

    def getEnd(self):
        return int(self.end)

    def getNoPages(self):
        return int(math.ceil(float(len(self.list)) / config.getint("admin.pageitems", 20)))

    def printPageList(self):
        order = self.req.params.get("order", "")
        ret = ''
        if self.page > 0:
            for p in range(1, self.getNoPages() + 1):
                b_class = "admin_page"
                if p == self.page:
                    b_class = "admin_page_act"
                ret += '<button type="submit" name="page" class="{0}" title="{1}" value="{2}">{2}</button>'.format(
                        b_class,
                        _core_translation.translate(self.language, "page"),
                        unicode(p),
                    )
        if len(ret) == 0:
            return ""
        return '[' + ret + '] '

    def printPageAll(self):
        if self.page != 0:
            return '<button name="resetpage" title="{}" class="admin_page" type="submit" value="">{}</button>'.format(
                    _core_translation.translate(self.language, "admin_allelements_title"),
                    _core_translation.translate(self.language, "show_all"),
                )
        else:
            return '<button name="firstpage" title="{}" class="admin_page" type="submit" value="">{}</button>'.format(
                    _core_translation.translate(self.language, "admin_pageelements_title"),
                    _core_translation.translate(self.language, "admin_pageelements_title"),
                )

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
                        retList.append(Link(
                                "{}1".format(unicode(i)),
                                _core_translation.translate(self.language, "admin_sort_label"),
                                '{} <img src="/static/img/az.png" border="0" />'.format(col),
                            ))
                    else:
                        retList.append(Link(
                                "{}0".format(unicode(i)),
                                _core_translation.translate(self.language, "admin_sort_label"),
                                '{} <img src="/static/img/za.png" border="0" />'.format(col),
                            ))
                else:
                    retList.append(Link(
                            "{}0".format(unicode(i)),
                            _core_translation.translate(self.language, "admin_sort_label"),
                            col,
                        ))
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


""" main method for content area """

@ensure_unicode_returned(name="adminutils.show_content")
def show_content(req, op):

    user = users.user_from_session()
    if not user.is_admin:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/admin/frame.html", macro="errormessage", request=req)
    else:
        if op == "" or op not in get_menu_strings(_menu):
            if op != "memstats":
                op = "menumain"
        module = adminModules[op.split("_")[0]]

        if op.find("_") > -1:
            return module.spc(req, op)
        else:
            return module.validate(req, op)


def adminNavigation():
    return parse_menu_struct(_menu)


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
    p = path.split('/')
    for item in menulist:
        for subitem in item.getItemList():
            if subitem.getName() == p[0]:
                return map("admin_menu_{}".format,(item.name,subitem.name))

    return ("admin_menu_menumain",)


def become_user(login_name, authenticator_key=None):
    """Changes current user to the user specified by `login_name` and returns the user object.
    If there are multiple results for a `login_name`, an authenticator_key must be given.
    Can only be called when the current user is admin.
    """
    user = users.user_from_session()
    if not user.is_admin:
        raise SecurityException("becoming other users not allowed for non-admin users")

    candidate_users = q(User).filter_by(login_name=login_name).all()
    if not candidate_users:
        raise ValueError("unknown user login name " + login_name)

    user, = candidate_users
    _flask.session["user_id"] = user.id
    return user
