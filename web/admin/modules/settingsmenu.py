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
import core.config as config

from utils.utils import parseMenuString
from web.admin.adminutils import adminNavigation, getAdminModuleInformation, adminModules
from web.edit.edit import getEditModules, editModules, get_edit_menu_tabs
from core.systemtypes import Root
from core import db
from core import Node
from contenttypes.data import Data

logg = logging.getLogger(__name__)
q = db.query


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

    try:
        nodeclass = Node.get_class_for_typestring(typename.lower())
    except KeyError:
        return {}

    if typename == "root":
        return {}

    _items = {}

    menu_str = get_edit_menu_tabs(nodeclass)

    if menu_str != "":
        menus[nodeclass.name] = parseMenuString(menu_str)
        _menu = {}
        _menu[-1] = []

        editModules = getEditModules()  # modules installed in system

        for module in editModules:
            if module.startswith("menu"):
                active = -1
                for m in menus[nodeclass.name]:
                    if m.getName().endswith(module):
                        active = menus[nodeclass.name].index(m)
                        break
                if active not in _menu.keys():
                    _menu[active] = []
                _menu[active].append(module)

            else:
                active = -1
                for m in menus[nodeclass.name]:
                    items = m.getItemList()
                    for item in items:
                        if item == module:
                            active = menus[nodeclass.name].index(m)
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
        root = q(Root).one()
        if key == "adminmodules_default":
            root.system_attrs["admin.menu"] = config.get("admin.defaultmenu", "")
            if not root.system_attrs["admin.menu"]:
                # load default admin.menu
                adminNavigation()
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
            root.system_attrs["admin.menu"] = ret[:-1]

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
            root.system_attrs["admin.menu"] = ret[:-1]
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
            root.system_attrs["admin.menu"] = ret
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
            root.system_attrs["admin.menu"] = ret[:-1]
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
            root.system_attrs["admin.menu"] = ret[:-1]
            break
    db.session.commit()


def editModuleActions(req):
    root = q(Root).one()
    datatype = req.params.get("datatype", "").lower()

    try:
        nodeclass = Node.get_class_for_typestring(datatype)
    except KeyError:
        logg.error("type %s not found", datatype)
        return

    for key in req.params.keys():
        if key == "editmodules_default":
            root.system_attrs["edit.menu." + datatype] = nodeclass.get_default_edit_menu_tabs()
            break

        elif key.startswith("del|"):
            ret = ""
            m = key.split("|")[-1][:-2]
            items = getEditModuleHierarchy(datatype)
            for k in items:
                if k >= 0 and not (m.startswith("menu") and items[k][0] == m):
                    i = [item for item in items[k] if item != m]
                    if len(i) > 1:
                        ret += i[0] + "(" + ";".join(i[1:]) + ");"
                    else:
                        ret += i[0] + "();"
            root.system_attrs["edit.menu." + datatype] = ret[:-1]
            break

        elif key.startswith("show|"):  # add menu
            item = key.split("|")[-1][:-2]
            menu_str = get_edit_menu_tabs(nodeclass) + ";" + item + "()"
            root.system_attrs["edit.menu." + datatype] = menu_str
            break

        elif key.startswith("move|") and req.params.get(key) != "":
            # move item to menu
            dest = req.params.get(key)
            dest_id = -1
            mod = key.split("|")[-1]
            items = getEditModuleHierarchy(datatype)
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
            root.system_attrs["edit.menu." + datatype] = ret[:-1]
            break

        elif key.startswith("up|"):
            # move module or module item up
            m = key[:-2].split("|")[-1]
            items = getEditModuleHierarchy(datatype)
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
            root.system_attrs["edit.menu." + datatype] = ret[:-1]
            break

        elif key.startswith("down|"):
            # move module or module item down
            m = key[:-2].split("|")[-1]
            items = getEditModuleHierarchy(datatype)
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
            root.system_attrs["edit.menu." + datatype] = ret[:-1]
            break
    db.session.commit()


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
        d = Data()
        for dtype in d.get_all_datatypes():
            if dtype.name != "root":
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
