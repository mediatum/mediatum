# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re
import logging
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
from schema.schema import fieldoption
from schema.schema import getMetaFieldTypeNames
from schema.schema import getMetaType
import core.translation as _translation
import schema.schema as _schema
from core import db
from web import admin as _web_admin

q = db.query

logg = logging.getLogger(__name__)


""" list all fields of given metadatatype """


def showDetailList(req, id):
    metadatatype = getMetaType(id)
    metafields = metadatatype.getMetaFields()
    metafields_dependencies = _schema._get_metafields_dependencies()
    used_by = {metafield.id:u"".join(
        u"\n{schema_name}: {mask_name}: {metafield_name}".format(**md._asdict())
        for md in metafields_dependencies
        if md.metafield_id == metafield.id or (
            md.maskitem_fieldtype in ('mapping', 'attribute')
            and
            int(md.maskitem_attribute) == metafield.id
           )
       ) for metafield in metafields}

    order = _web_admin.adminutils.getSortCol(req)
    actfilter = _web_admin.adminutils.getFilter(req)

    # resets filter to all if adding mask in /metatype view
    # if req.params.get('acttype') == 'mask' or req.params.get('acttype') == 'schema':
    #     if req.mediatum_contextfree_path == '/metatype' and 'filterbutton' not in req.params:
    #         actfilter = '*'

    # resets filter when going to a new view
    if 'filterbutton' not in req.params:
        actfilter = '*'

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", _translation.translate(_translation.set_language(req.accept_languages), "all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            if req.params.get("filtertype", "") == "name":
                metafields = filter(lambda x: num.match(x.getName()), metafields)
            else:
                metafields = filter(lambda x: num.match(x.getLabel()), metafields)

        elif actfilter == "else" or actfilter == _translation.translate(_translation.set_language(req.accept_languages), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9]|\.)')
            if req.params.get("filtertype", "") == "name":
                metafields = filter(lambda x: not all.match(x.getName()), metafields)
            else:
                metafields = filter(lambda x: not all.match(x.getLabel()), metafields)
        else:
            if req.params.get("filtertype", "") == "name":
                metafields = filter(lambda x: x.getName().lower().startswith(actfilter), metafields)
            else:
                metafields = filter(lambda x: x.getLabel().lower().startswith(actfilter), metafields)

    pages = _web_admin.adminutils.Overview(req, metafields)

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            metafields.sort(lambda x, y: cmp(x.orderpos, y.orderpos))
        elif int(order[0:1]) == 1:
            metafields.sort(lambda x, y: cmp(x.getName().lower(), y.getName().lower()))
        elif int(order[0:1]) == 2:
            metafields.sort(lambda x, y: cmp(x.getLabel().lower(), y.getLabel().lower()))
        elif int(order[0:1]) == 3:
            metafields.sort(
                lambda x, y: cmp(getMetaFieldTypeNames()[ustr(x.getFieldtype())], getMetaFieldTypeNames()[ustr(y.getFieldtype())]))
        if int(order[1:]) == 1:
            metafields.reverse()

    v = _web_admin.adminutils.getAdminStdVars(req)
    v["filterattrs"] = [("name", "admin_metafield_filter_name"), ("label", "admin_metafield_filter_label")]
    v["filterarg"] = req.params.get("filtertype", "name")

    v["sortcol"] = pages.OrderColHeader(("",) + tuple(
        _translation.translate(
            _translation.set_language(req.accept_languages),
            "admin_metafield_col_{}".format(col),
            )
        for col in xrange(1, 4)
        ))
    v["metadatatype"] = metadatatype
    v["metafields"] = metafields
    v["used_by"] = used_by
    v["fieldoptions"] = fieldoption
    v["fieldtypes"] = getMetaFieldTypeNames()
    v["pages"] = pages
    v["actfilter"] = actfilter

    v["actpage"] = req.params.get("actpage")
    v["csrf"] = _core_csrfform.get_token()
    v["translate"] = _translation.translate
    v["language"] = _translation.set_language(req.accept_languages)
    if ustr(req.params.get("page", "")).isdigit():
        v["actpage"] = req.params.get("page")

    return _tal.processTAL(v, file="web/admin/modules/metatype_field.html", macro="view_field", request=req)
