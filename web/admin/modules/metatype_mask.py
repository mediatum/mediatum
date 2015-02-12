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
import re

import core.tree as tree
import core.config as config
from web.admin.adminutils import Overview, getAdminStdVars, getSortCol, getFilter
from schema.schema import getMetaType, getMaskTypes
from core.translation import lang, t
from schema.mapping import getMappings
from utils.utils import removeEmptyStrings
from web.common.acl_web import makeList


""" mask overview """


def showMaskList(req, id):
    metadatatype = getMetaType(id)
    masks = metadatatype.getMasks()
    order = getSortCol(req)
    actfilter = getFilter(req)

    # resets filter to all if adding mask in /metatype view
    # if req.params.get('acttype') == 'mask' or req.params.get('acttype') == 'schema':
    #     if req.path == '/metatype' and 'filterbutton' not in req.params:
    #         actfilter = '*'

    # resets filter when going to a new view
    if 'filterbutton' not in req.params:
        actfilter = '*'

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", t(lang(req), "admin_filter_all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            masks = filter(lambda x: num.match(x.getName()), masks)

        elif actfilter == "else" or actfilter == t(lang(req), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            masks = filter(lambda x: not all.match(x.getName()), masks)
        else:
            masks = filter(lambda x: x.getName().lower().startswith(actfilter), masks)

    pages = Overview(req, masks)

    defaults = {}
    for mask in masks:
        if mask.getDefaultMask():
            defaults[mask.getMasktype()] = mask.id

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            masks.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))
        elif int(order[0:1]) == 1:
            masks.sort(lambda x, y: cmp(x.getMasktype(), y.getMasktype()))
        elif int(order[0:1]) == 2:
            masks.sort(lambda x, y: cmp(x.getDescription(), y.getDescription()))
        elif int(order[0:1]) == 3:
            masks.sort(lambda x, y: cmp(x.getDefaultMask(), y.getDefaultMask()))
        elif int(order[0:1]) == 4:
            masks.sort(lambda x, y: cmp(x.getLanguage(), y.getLanguage()))
        if int(order[1:]) == 1:
            masks.reverse()
    else:
        masks.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))

    v = getAdminStdVars(req)
    v["filterattrs"] = []
    v["filterarg"] = req.params.get("filtertype", "name")
    v["sortcol"] = pages.OrderColHeader(
        [
            t(
                lang(req), "admin_mask_col_1"), t(
                lang(req), "admin_mask_col_2"), t(
                    lang(req), "admin_mask_col_3"), t(
                        lang(req), "admin_mask_col_4"), t(
                            lang(req), "admin_mask_col_5"), t(
                                lang(req), "admin_mask_col_6")])
    v["metadatatype"] = metadatatype
    v["masktypes"] = getMaskTypes()
    v["lang_icons"] = {"de": "/img/flag_de.gif", "en": "/img/flag_en.gif", "no": "/img/emtyDot1Pix.gif"}
    v["masks"] = masks
    v["pages"] = pages
    v["order"] = order
    v["defaults"] = defaults

    v["order"] = order
    v["actfilter"] = actfilter
    return req.getTAL("web/admin/modules/metatype_mask.html", v, macro="view_mask")

""" mask details """


def MaskDetails(req, pid, id, err=0):
    mtype = getMetaType(pid)

    if err == 0 and id == "":
        # new mask
        mask = tree.Node(u"", type="mask")

    elif id != "" and err == 0:
        # edit mask
        if id.isdigit():
            mask = tree.getNode(id)
        else:
            mask = mtype.getMask(id)

    else:
        # error filling values
        mask = tree.Node(req.params.get("mname", ""), type="mask")
        mask.setDescription(req.params.get("mdescription", ""))
        mask.setMasktype(req.params.get("mtype"))
        mask.setLanguage(req.params.get("mlanguage", ""))
        mask.setDefaultMask(req.params.get("mdefault", False))

    v = getAdminStdVars(req)
    v["mask"] = mask
    v["mappings"] = getMappings()
    v["mtype"] = mtype
    v["error"] = err
    v["pid"] = pid
    v["masktypes"] = getMaskTypes()
    v["id"] = id
    v["langs"] = config.get("i18n.languages").split(",")
    v["actpage"] = req.params.get("actpage")

    rule = mask.getAccess("read")
    if rule:
        rule = rule.split(",")
    else:
        rule = []

    rights = removeEmptyStrings(rule)
    v["acl"] = makeList(req, "read", rights, {}, overload=0, type="read")

    return req.getTAL("web/admin/modules/metatype_mask.html", v, macro="modify_mask")
