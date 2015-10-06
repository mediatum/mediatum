"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2009 Matthias Kramm <kramm@in.tum.de>

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
from utils.utils import formatTechAttrs, dec_entry_log
from utils.date import format_date, parse_date
from core.transition import httpstatus
from core import Node, db
from core.transition import current_user

q = db.query
logg = logging.getLogger(__name__)


@dec_entry_log
def getContent(req, ids):
    node = q(Node).get(ids[0])
    if not node.has_write_access() or "admin" in current_user.hidden_edit_functions:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if req.params.get('action') == 'getsearchdata':
        req.writeTAL("web/edit/modules/admin.html", {'searchdata': node.search('searchcontent=%s' % node.id), 'node': node}, macro="searchdata")
        return ''

    if req.params.get("type", "") == "addattr" and req.params.get("new_name", "") != "" and req.params.get("new_value", "") != "":
        node.attrs[req.params.get("new_name")] = req.params.get("new_value", "")
        db.session.commit()
        logg.info("new attribute %s for node %s added", req.params.get("new_name", ""), node.id)

    for key in req.params.keys():
        # update localread value of current node
        if key.startswith("del_localread"):
            node.resetLocalRead()
            logg.info("localread attribute of node %s updated", node.id)
            break

        # remove  attribute
        if key.startswith("attr_"):
            del node.attrs[key[5:-2]]
            db.session.commit()
            logg.info("attribute %s of node %s removed", key[5:-2], node.id)
            break

    metadatatype = node.metadatatype
    fieldnames = []

    if metadatatype:
        fields = metadatatype.getMetaFields()
        for field in fields:
            fieldnames += [field.name]
    else:
        fields = []

    attrs = node.attrs.items()

    metafields = {}
    technfields = {}
    obsoletefields = {}

    tattr = {}
    try:
        tattr = node.getTechnAttributes()
    except AttributeError:
        pass
    tattr = formatTechAttrs(tattr)

    for key, value in attrs:
        if key in fieldnames:
            metafields[key] = formatdate(value, getFormat(fields, key))
        elif key in tattr.keys():
            technfields[key] = formatdate(value)
        else:
            obsoletefields[key] = value

    # remove all technical attributes
    if req.params.get("type", "") == "technical":
        for key in technfields:
            del node.attrs[key]
        technfields = {}
        logg.info("technical attributes of node %s removed", node.id)

    return req.getTAL("web/edit/modules/admin.html", {"id": req.params.get("id", "0"),
                                                      "tab": req.params.get("tab", ""),
                                                      "node": node,
                                                      "obsoletefields": obsoletefields,
                                                      "metafields": metafields,
                                                      "fields": fields,
                                                      "technfields": technfields,
                                                      "tattr": tattr,
                                                      "fd": formatdate,
                                                      "gf": getFormat,
                                                      "adminuser": current_user.is_admin,
                                                      "canedit": node.has_write_access()},
                      macro="edit_admin_file")


def getFormat(fields, name):
    for field in fields:
        if field.name == name:
            return field.getValues()


def formatdate(value, f='%d.%m.%Y %H:%M:%S'):
    if not isinstance(value, unicode):
        value = unicode(value)
    try:
        return format_date(parse_date(value, "%Y-%m-%dT%H:%M:%S"), format=f)
    except ValueError:
        return value
