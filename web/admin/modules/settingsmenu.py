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

import core.config as config
import core.tree as tree

from utils.utils import parseMenuString
from web.admin.adminutils import adminNavigation, getAdminModuleInformation, adminModules
from web.edit.edit import getEditModules, editModules, getEditMenuString
from core.tree import getRoot
from core.datatypes import loadAllDatatypes


def getInformation():
    return {"version": "1.0", "required": 1}


def validate(req, op):
    return view(req)


def ItemIsRequired(module):
    for key in adminModules:
        if key == module:
            inf = adminModules[key].getInformation()
            if "required" in inf.keys():
                return inf["required"]
    return 0


def getAdminModuleHierarchy():
    _menu = {}
    _menu[-1] = []

    _items = {}
    adminMenus = adminNavigation()  # activated menuitems
    for module in adminModules:
        if module.startswith("menu"):
            active = -1
            for m in adminMenus:
                if m.getName() == module:
                    active = adminMenus.index(m)
                    break
            if active not in _menu.keys():
                _menu[active] = []
            _menu[active].append(module)
        else:
            active = -1
            for m in adminMenus:
                items = m.getItemList()
                for item in items:
                    if item == module:
                        active = adminMenus.index(m)
                        if active not in _items.keys():
                            _items[active] = []
                        _items[active].append((module, items.index(item)))
                        break
            if active == -1:
                if active not in _items.keys():
                    _items[active] = []
                _items[active].append((module, 0))

    for key in _menu.keys():
        if key in _items.keys():
            items = _items[key]
            items.sort(lambda x, y: cmp(x[0], y[0]))
            for item in items:
                _menu[key].append(item[0])
    return _menu


def getEditModuleHierarchy(typename):
    _menu = {}
    menus = {}
    types = []

    for type in loadAllDatatypes():
        if type.name == typename:
            types = [type]
            break

    for dtype in types:  # get menu for type
        _items = {}
        if dtype.name != "root":
            n = tree.Node(u"", type=dtype.name)
            menu_str = getEditMenuString(dtype.name)

            if menu_str != "":
                menus[n.type] = parseMenuString(menu_str)
                _menu = {}
                _menu[-1] = []

                editModules = getEditModules()  # modules installed in system

                for module in editModules:
                    if module.startswith("menu"):
                        active = -1
                        for m in menus[n.type]:
                            if m.getName().endswith(module):
                                active = menus[n.type].index(m)
                                break
                        if active not in _menu.keys():
                            _menu[active] = []
                        _menu[active].append(module)

                    else:
                        active = -1
                        for m in menus[n.type]:
                            items = m.getItemList()
                            for item in items:
                                if item == module:
                                    active = menus[n.type].index(m)
                                    if active not in _items.keys():
                                        _items[active] = []
                                    _items[active].append((module, items.index(item)))
                                    break

                        if active == -1:
                            if active not in _items.keys():
                                _items[active] = []
                            _items[active].append((module, 0))

                for key in _menu.keys():
                    if key in _items.keys():
                        items = _items[key]
                        items.sort(lambda x, y: cmp(x[1], y[1]))
                        for item in items:
                            _menu[key].append(item[0])
    return _menu


def adminModuleActions(req):
    for key in req.params.keys():
        if key == "adminmodules_default":
            getRoot().set("admin.menu", config.get("admin.defaultmenu"))
            break

        elif key.startswith("move|") and req.params.get(key) != "":
            # move item to menu
            dest = req.params.get(key)
            dest_id = -1
            mod = key.split("|")[-1]
            items = getAdminModuleHierarchy()
            for k in items:
                if dest in items[k]:
                    dest_id = k
                if mod in items[k]:
                    items[k].remove(mod)
            items[dest_id].append(mod)
            ret = ""
            for k in items:
                if len(items[k]) == 0:
                    pass
                elif items[k][0].startswith("menu"):
                    ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
            getRoot().set("admin.menu", ret[:-1])

        elif key.startswith("hide|"):
            # hide module
            m = key[:-2].split("|")[-1]
            ret = ""
            items = getAdminModuleHierarchy()
            for k in items:
                if k >= 0 and not (m.startswith("menu") and items[k][0] == m):
                    i = [item for item in items[k] if item != m]
                    if len(i) > 1:
                        ret += i[0] + "(" + ";".join(i[1:]) + ");"
                    else:
                        ret += i[0] + "();"
            getRoot().set("admin.menu", ret[:-1])
            break

        elif key.startswith("show|"):
            # show module (menu)
            ret = ""
            m = key[:-2].split("|")[-1]
            items = getAdminModuleHierarchy()
            for k in items:
                if k >= 0:
                    if len(items[k]) > 1:
                        ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
                    else:
                        ret += items[k][0] + "();"

            if m.startswith("menu"):
                ret += m + "()"
            elif len(ret) > 2:
                ret = ret[:-2] + ";" + m + ")"
            getRoot().set("admin.menu", ret)
            break

        elif key.startswith("up|"):
            # move module or module item up
            m = key[:-2].split("|")[-1]
            items = getAdminModuleHierarchy()
            for k in items:
                if m in items[k] and items[k].index(m) == 0:  # menu
                    src = items[k]
                    items[k] = items[k - 1]
                    items[k - 1] = src
                    break

                elif m in items[k] and items[k].index > 0:  # menu item
                    src_id = items[k].index(m)
                    items[k][src_id] = items[k][src_id - 1]
                    items[k][src_id - 1] = m
                    break

            ret = ""
            for k in items:
                if len(items[k]) == 0:
                    pass
                elif items[k][0].startswith("menu"):
                    ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
            getRoot().set("admin.menu", ret[:-1])
            break

        elif key.startswith("down|"):
            # move module or module item down
            m = key[:-2].split("|")[-1]
            items = getAdminModuleHierarchy()
            for k in items:
                if m in items[k] and items[k].index(m) == 0:  # menu
                    src = items[k]
                    items[k] = items[k + 1]
                    items[k + 1] = src
                    break

                elif m in items[k] and items[k].index > 0:  # menu item
                    src_id = items[k].index(m)
                    items[k][src_id] = items[k][src_id + 1]
                    items[k][src_id + 1] = m
                    break

            ret = ""
            for k in items:
                if len(items[k]) == 0:
                    pass
                elif items[k][0].startswith("menu"):
                    ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
            getRoot().set("admin.menu", ret[:-1])
            break


def editModuleActions(req):
    for key in req.params.keys():
        if key == "editmodules_default":
            type = req.params.get("datatype")
            getRoot().set("edit.menu." + type, getEditMenuString(type, default=1))
            break

        elif key.startswith("del|"):
            ret = ""
            m = key.split("|")[-1][:-2]
            type = req.params.get("datatype")
            items = getEditModuleHierarchy(type)
            for k in items:
                if k >= 0 and not (m.startswith("menu") and items[k][0] == m):
                    i = [item for item in items[k] if item != m]
                    if len(i) > 1:
                        ret += i[0] + "(" + ";".join(i[1:]) + ");"
                    else:
                        ret += i[0] + "();"
            getRoot().set("edit.menu." + type, ret[:-1])
            break

        elif key.startswith("show|"):  # add menu
            item = key.split("|")[-1][:-2]
            type = req.params.get("datatype")
            menu_str = getEditMenuString(type) + ";" + item + "()"
            getRoot().set("edit.menu." + type, menu_str)
            break

        elif key.startswith("move|") and req.params.get(key) != "":
            # move item to menu
            dest = req.params.get(key)
            dest_id = -1
            mod = key.split("|")[-1]
            type = req.params.get("datatype")
            items = getEditModuleHierarchy(type)
            for k in items:
                if dest in items[k]:
                    dest_id = k
                if mod in items[k]:
                    items[k].remove(mod)
            items[dest_id].append(mod)

            ret = ""
            for k in items:
                if len(items[k]) == 0 or k < 0:
                    pass
                elif items[k][0].startswith("menu"):
                    ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
            getRoot().set("edit.menu." + type, ret[:-1])
            break

        elif key.startswith("up|"):
            # move module or module item up
            m = key[:-2].split("|")[-1]
            type = req.params.get("datatype")
            items = getEditModuleHierarchy(type)
            for k in items:
                if m in items[k] and items[k].index(m) == 0:  # menu
                    src = items[k]
                    items[k] = items[k - 1]
                    items[k - 1] = src
                    break

                elif m in items[k] and items[k].index > 0:  # menu item
                    src_id = items[k].index(m)
                    items[k][src_id] = items[k][src_id - 1]
                    items[k][src_id - 1] = m
                    break

            ret = ""
            for k in items:
                if len(items[k]) == 0 or k < 0:
                    pass
                elif items[k][0].startswith("menu"):
                    ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
            getRoot().set("edit.menu." + type, ret[:-1])
            break

        elif key.startswith("down|"):
            # move module or module item down
            m = key[:-2].split("|")[-1]
            type = req.params.get("datatype")
            items = getEditModuleHierarchy(type)
            for k in items:
                if m in items[k] and items[k].index(m) == 0:  # menu
                    src = items[k]
                    items[k] = items[k + 1]
                    items[k + 1] = src
                    break

                elif m in items[k] and items[k].index > 0:  # menu item
                    src_id = items[k].index(m)
                    items[k][src_id] = items[k][src_id + 1]
                    items[k][src_id + 1] = m
                    break

            ret = ""
            for k in items:
                if len(items[k]) == 0 or k < 0:
                    pass
                elif items[k][0].startswith("menu"):
                    ret += items[k][0] + "(" + ";".join(items[k][1:]) + ");"
            getRoot().set("edit.menu." + type, ret[:-1])
            break


def view(req):
    page = req.params.get("page", "")
    gotopage = req.params.get("gotopage", "")

    if gotopage == "adminmodules" and req.params.get("changes") == "adminmodules":
        adminModuleActions(req)

    elif gotopage == "editmodules" and req.params.get("changes") == "editmodules":
        editModuleActions(req)

    v = {}

    v["gotopage"] = req.params.get("gotopage", "")
    v["subitem"] = req.params.get("editsubitem", "")

    if page == "adminmodules":
        v['mods'] = getAdminModuleHierarchy()
        v['modinfo'] = getAdminModuleInformation
        v['required'] = ItemIsRequired
        return req.getTAL("web/admin/modules/settingsmenu.html", v, macro="view_adminmodules")

    elif page == "editmodules":

        if "subitem" not in v or v["subitem"] == "":
            v["subitem"] = req.params.get("subitem", "")
        v['mods'] = getEditModuleHierarchy(req.params.get("subitem", ""))
        v['datatypes'] = []
        v["typelongname"] = ""
        for dtype in loadAllDatatypes():
            if dtype.name != "root":
                n = tree.Node(u"", type=dtype.name)
                if hasattr(n, "getEditMenuTabs"):
                    v['datatypes'].append(dtype)
            if dtype.name == v["subitem"]:
                v["typelongname"] = dtype.getLongName()
        modinfo = {}
        for mod in editModules:
            if hasattr(editModules[mod], "getInformation"):
                modinfo[mod] = editModules[mod].getInformation()

        def getVersion(modname):
            if modname in modinfo:
                if "version" in modinfo[modname]:
                    return modinfo[modname]["version"]
            return ""

        def isSystem(modname):
            if modname in modinfo:
                if "system" in modinfo[modname] and modinfo[modname]["system"] == 1:
                    return 1
            return 0

        v["getVersion"] = getVersion
        v["isSystem"] = isSystem
        return req.getTAL("web/admin/modules/settingsmenu.html", v, macro="view_editmodules")

    else:
        return req.getTAL("web/admin/modules/settingsmenu.html", v, macro="view")
