# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

from web.admin.adminutils import adminNavigation, adminModules


def getInformation(attribute=""):
    attributes = {"icon": "",
                  "required": 1,
                  "version": "1.0"}
    if attribute != "":
        if attribute in attributes.keys():
            return attributes[attribute]
        else:
            return ""
    return attributes


def validate(req, op):
    v = {}
    items = []
    for menu in adminNavigation():
        itemdata = {}
        itemdata["name"] = menu.getName()
        itemdata["icon"] = adminModules[menu.getName()].getInformation("icon")
        itemdata["submenu"] = menu.getItemList()

        items.append(itemdata)
    v["navitems"] = items
    return _tal.processTAL(v, file="/web/admin/modules/menumain.html", macro="view", request=req)
