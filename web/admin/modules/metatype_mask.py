# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from web.admin.adminutils import Overview, getAdminStdVars, getSortCol, getFilter
import schema.schema as _schema
from schema.schema import getMetaType
from core import db

q = db.query

""" mask overview """


def showMaskList(req, id):
    metadatatype = getMetaType(id)
    masks = metadatatype.getMasks()
    order = getSortCol(req)
    actfilter = getFilter(req)

    # resets filter to all if adding mask in /metatype view
    # if req.params.get('acttype') == 'mask' or req.params.get('acttype') == 'schema':
    #     if req.mediatum_contextfree_path == '/metatype' and 'filterbutton' not in req.params:
    #         actfilter = '*'

    # resets filter when going to a new view
    if 'filterbutton' not in req.params:
        actfilter = '*'

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", _core_translation.translate(_core_translation.set_language(req.accept_languages), "all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            masks = filter(lambda x: num.match(x.name), masks)

        elif actfilter == "else" or actfilter == _core_translation.translate(_core_translation.set_language(req.accept_languages), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            masks = filter(lambda x: not all.match(x.name), masks)
        else:
            masks = filter(lambda x: x.name.lower().startswith(actfilter), masks)

    pages = Overview(req, masks)

    defaults = {}
    for mask in masks:
        if mask.getDefaultMask():
            defaults[mask.getMasktype()] = mask.id

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            masks.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))
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
    v["sortcol"] = pages.OrderColHeader(tuple(
        _core_translation.translate(
            _core_translation.set_language(req.accept_languages),
            "admin_mask_col_{}".format(col),
            )
        for col in xrange(1, 7)
        ))
    v["metadatatype"] = metadatatype
    v["masktypes"] = _schema.masktypes
    v["lang_icons"] = {"de": "/static/img/flag_de.gif", "en": "/static/img/flag_en.gif", "no": "/static/img/emtyDot1Pix.gif"}
    v["masks"] = masks
    v["pages"] = pages
    v["order"] = order
    v["defaults"] = defaults

    v["order"] = order
    v["actfilter"] = actfilter
    v["csrf"] = _core_csrfform.get_token()
    return _tal.processTAL(v, file="web/admin/modules/metatype_mask.html", macro="view_mask", request=req)
