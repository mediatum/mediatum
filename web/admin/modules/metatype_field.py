# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re
import inspect
import logging
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import utils.utils as _utils_utils
from web.admin.adminutils import Overview, getAdminStdVars, getSortCol, getFilter
from schema.schema import Metadatatype
from schema.schema import fieldoption
from schema.schema import getFieldsForMeta
from schema.schema import getMetaField
from schema.schema import getMetaFieldTypeNames
from schema.schema import getMetaType
from schema.schema import getMetadataType
import core.translation as _translation
from schema.schema import Metafield
import schema.schema as _schema
from core import Node
from core import db

q = db.query

logg = logging.getLogger(__name__)


""" list all fields of given metadatatype """


def showDetailList(req, id):
    metadatatype = getMetaType(id)
    metafields = metadatatype.getMetaFields()
    metafields_dependencies = _schema._get_metafields_dependencies()
    used_by = {metafield.id: u"".join(u"\n{schema_name}: {mask_name}: {metafield_name}".format(**md._asdict())
                                         for md in metafields_dependencies if md.metafield_id == metafield.id)
               for metafield in metafields}

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
        if actfilter in ("all", "*", _translation.t(_translation.set_language(req.accept_languages), "admin_filter_all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            if req.params.get("filtertype", "") == "name":
                metafields = filter(lambda x: num.match(x.getName()), metafields)
            else:
                metafields = filter(lambda x: num.match(x.getLabel()), metafields)

        elif actfilter == "else" or actfilter == _translation.t(_translation.set_language(req.accept_languages), "admin_filter_else"):
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

    pages = Overview(req, metafields)

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
    else:
        metafields.sort(lambda x, y: cmp(x.orderpos, y.orderpos))

    v = getAdminStdVars(req)
    v["filterattrs"] = [("name", "admin_metafield_filter_name"), ("label", "admin_metafield_filter_label")]
    v["filterarg"] = req.params.get("filtertype", "name")

    v["sortcol"] = pages.OrderColHeader(("",) + tuple(
        _translation.t(
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
    v["order"] = order
    v["actfilter"] = actfilter

    v["actpage"] = req.params.get("actpage")
    v["csrf"] = _core_csrfform.get_token()
    v["translate"] = _translation.translate
    v["language"] = _translation.set_language(req.accept_languages)
    if ustr(req.params.get("page", "")).isdigit():
        v["actpage"] = req.params.get("page")

    return _tal.processTAL(v, file="web/admin/modules/metatype_field.html", macro="view_field", request=req)


""" form for field of given metadatatype (edit/new) """


def FieldDetail(req, name=None, error=None):
    name = name or req.params.get("orig_name", "")
    if name != "":  # edit field, irrespective of error
        field = q(Metadatatype).get(req.params.get("parent")).children
        field = field.filter_by(name=name, type=u'metafield').scalar()
    elif error:  # new field, with error filling values
        field = Metafield(req.params.get("mname") or req.params.get("orig_name"))
        field.setLabel(req.params.get("mlabel"))
        field.setOrderPos(req.params.get("orderpos"))
        field.setFieldtype(req.params.get("mtype"))
        field.setOption("".join(key[7] for key in req.params if key.startswith("option_")))
        field.setDescription(req.params.get("mdescription"))
        db.session.commit()
    else:  # new field, no error (yet)
        field = Metafield(u"")
        db.session.commit()

    metadatatype = getMetaType(req.params.get("parent"))
    tal_ctx = getAdminStdVars(req)
    tal_ctx.update(
            actpage=req.params.get("actpage"),
            adminfields="",
            csrf= _core_csrfform.get_token(),
            error=error,
            fieldoptions=fieldoption,
            fieldtypes=getMetaFieldTypeNames(),
            filtertype=req.params.get("filtertype", ""),
            metadatatype=metadatatype,
            metafield=field,
            metafields={fields.name:fields for fields in getFieldsForMeta(req.params.get("parent"))},
            valuelist=field.getValueList(),
           )

    if field.id:
        tal_ctx["field"] = field
        tal_ctx["adminfields"] = getMetadataType(field.getFieldtype()).get_metafieldeditor_html(
                field,
                metadatatype,
                _translation.set_language(req.accept_languages),
            )

    if field.getFieldtype() == "url":
        tal_ctx["valuelist"].extend(("",)*4)
        tal_ctx["valuelist"] = tal_ctx["valuelist"][:4]

    db.session.commit()
    return _tal.processTAL(
            tal_ctx,
            file="web/admin/modules/metatype_field.html",
            macro="modify_field" if field.id else "new_field",
            request=req,
           )
