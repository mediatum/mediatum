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


import core.acl as acl
import core.users as users
import logging
from utils.utils import formatTechAttrs, dec_entry_log
from utils.date import format_date, parse_date
from core.transition import httpstatus


logg = logging.getLogger(__name__)


@dec_entry_log
def getContent(req, ids):
    user = users.getUserFromRequest(req)
    node = tree.getNode(ids[0])
    access = acl.AccessData(req)
    if not access.hasWriteAccess(node) or "admin" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if req.params.get('action') == 'getsearchdata':
        req.writeTAL("web/edit/modules/admin.html", {'searchdata': node.search('searchcontent=%s' % node.id), 'node': node}, macro="searchdata")
        return ''

    if req.params.get("type", "") == "addattr" and req.params.get("new_name", "") != "" and req.params.get("new_value", "") != "":
        node.set(req.params.get("new_name", ""), req.params.get("new_value", ""))
        logg.info("new attribute %s for node %s added", req.params.get("new_name", ""), node.id)

    for key in req.params.keys():
        # update localread value of current node
        if key.startswith("del_localread"):
            node.resetLocalRead()
            logg.info("localread attribute of node %s updated", node.id)
            break

        # set current node 'dirty' (reindex for search)
        if key.startswith("set_dirty"):
            node.setDirty()
            logg.info("set node %s dirty", node.id)

            if node.isContainer():
                for child_node in node.getChildren():
                    child_node.setDirty()
                    logg.info("set node %s dirty", child_node.id)
            break

        # delete node from cache (e.g. after changes in db)
        if key.startswith("del_cache"):
            for n in node.getAllChildren():
                remove_from_nodecaches(n)
            break

        # remove  attribute
        if key.startswith("attr_"):
            node.removeAttribute(key[5:-2])
            logg.info("attribute %s of node %s removed", key[5:-2], node.id)
            break

    fields = node.getType().getMetaFields()
    fieldnames = []
    for field in fields:
        fieldnames += [field.name]

    attrs = node.items()

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
            node.removeAttribute(key)
        technfields = {}
        logg.info("technical attributes of node %s removed", node.id)

    return req.getTAL("web/edit/modules/admin.html", {"id": req.params.get("id", "0"), "tab": req.params.get("tab", ""), "node": node, "obsoletefields": obsoletefields, "metafields": metafields, "fields": fields, "technfields": technfields, "tattr": tattr, "fd": formatdate, "gf": getFormat, "adminuser": user.isAdmin(), "canedit": access.hasWriteAccess(node)}, macro="edit_admin_file")


def getFormat(fields, name):
    for field in fields:
        if field.name == name:
            return field.getValues()


def formatdate(value, f='%d.%m.%Y %H:%M:%S'):
    try:
        return format_date(parse_date(value, "%Y-%m-%dT%H:%M:%S"), format=f)
    except ValueError:
        return value
