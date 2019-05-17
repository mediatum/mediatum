"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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
