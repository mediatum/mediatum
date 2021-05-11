# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
from utils.utils import formatTechAttrs, suppress
from utils.date import format_date, parse_date
from core import httpstatus
from core import Node, db
from core.users import user_from_session
from collections import OrderedDict
from utils.compat import iteritems

q = db.query
logg = logging.getLogger(__name__)


def getContent(req, ids):
    user = user_from_session()
    node = q(Node).get(ids[0])
    if not node.has_write_access() or "admin" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if req.params.get("type", "") == "addattr" and req.params.get("new_name", "") != "" and req.params.get("new_value", "") != "":
        attrname = req.form.get("new_name")
        attrvalue = req.form.get("new_value")
        if attrname.startswith("system."):
            if user.is_admin:
                node.system_attrs[attrname[7:]] = attrvalue
            else:
            # non-admin user may not add / change system attributes, silently ignore the request.
            # XXX: an error msg would be better
                logg.warning(
                    "denied writing a system attribute because user is not an admin user, node=%s attrname=%s current_user=%s",
                    node.id,
                    attrname,
                    user.id,
                )
                return httpstatus.HTTP_FORBIDDEN

        node.set(attrname, attrvalue)
        db.session.commit()
        logg.info("new attribute %s for node %s added", req.params.get("new_name", ""), node.id)

    for key in req.params.keys():
        # update localread value of current node
        if key.startswith("del_localread"):
            node.resetLocalRead()
            logg.info("localread attribute of node %s updated", node.id)
            break

        # removing attributes only allowed for admin user

        # remove attribute
        if key.startswith("attr_"):
            if not user.is_admin:
                return httpstatus.HTTP_FORBIDDEN

            del node.attrs[key[5:-2]]
            db.session.commit()
            logg.info("attribute %s of node %s removed", key[5:-2], node.id)
            break

        # remove system attribute
        if key.startswith("system_attr_"):
            if not user.is_admin:
                return httpstatus.HTTP_FORBIDDEN

            attrname = key[12:-2]
            del node.system_attrs[attrname]
            db.session.commit()
            logg.info("system attribute %s of node %s removed", attrname, node.id)
            break

    metadatatype = node.metadatatype
    fieldnames = []

    if metadatatype:
        fields = metadatatype.getMetaFields()
        for field in fields:
            fieldnames += [field.name]
    else:
        fields = []

    metafields = OrderedDict()
    technfields = OrderedDict()
    obsoletefields = OrderedDict()
    system_attrs = []

    tattr = {}
    with suppress(AttributeError, warn=False):
        tattr = node.getTechnAttributes()
    tattr = formatTechAttrs(tattr)

    for key, value in sorted(iteritems(node.attrs), key=lambda t: t[0].lower()):
        if value or user.is_admin:
            # display all values for admins, even if they are "empty" (= a false value)
            if (key in fieldnames) or (key in tattr.keys()):
                metafields[key] = _format_date(value)
            else:
                obsoletefields[key] = value

    for key, value in sorted(iteritems(node.system_attrs), key=lambda t: t[0].lower()):
        system_attrs.append((key, value))

    # remove all technical attributes
    if req.params.get("type", "") == "technical":
        for key in technfields:
            del node.attrs[key]
        technfields = {}
        logg.info("technical attributes of node %s removed", node.id)

    return _tal.processTAL(
            dict(
                srcnodeid=req.values.get("srcnodeid", ""),
                id=req.params.get("id", "0"),
                tab=req.params.get("tab", ""),
                node=node,
                obsoletefields=obsoletefields,
                metafields=metafields,
                system_attrs=system_attrs,
                fields=fields,
                technfields=technfields,
                tattr=tattr,
                fd=_format_date,
                user_is_admin=user.is_admin,
                canedit=node.has_write_access(),
                csrf=_core_csrfform.get_token(),
            ),
            file="web/edit/modules/admin.html",
            macro="edit_admin_file",
            request=req,
        )


def _format_date(value, f='%d.%m.%Y %H:%M:%S'):
    if not isinstance(value, unicode):
        value = unicode(value)
    try:
        return format_date(parse_date(value, "%Y-%m-%dT%H:%M:%S"), format=f)
    except ValueError:
        return value
