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

import core.tree as tree
import core.acl as acl
import core.users as users
from utils.utils import formatTechAttrs
import logging

from core.tree import nodes_cache


def edit_admin(req, ids):
    user = users.getUserFromRequest(req)
    node = tree.getNode(ids[0])
    access = acl.AccessData(req)
    if not access.hasWriteAccess(node) or "admin" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    if req.params.get("type","")=="addattr" and req.params.get("new_name", "")!="" and req.params.get("new_value", "")!="":
        node.set(req.params.get("new_name", ""), req.params.get("new_value", ""))
        logging.getLogger('editor').info("new attribute "+str(req.params.get("new_name", ""))+" for node "+str(node.id)+" added")
        
    for key in req.params.keys():
        # update localread value of current node
        if key.startswith("del_localread"):
            node.resetLocalRead()
            logging.getLogger('editor').info("localread attribute of node "+str(node.id)+" updated")
            break
        
        # set current node 'dirty' (reindex for search)
        if key.startswith("set_dirty"):
            node.setDirty()
            logging.getLogger('editor').info("set node "+str(node.id)+" dirty")
            break
        
        # delete node from cache (e.g. after changes in db)
        if key.startswith("del_cache"):
            for n in node.getAllChildren():
                nodes_cache.remove(int(n.id))
            break
        
        # remove  attribute
        if key.startswith("attr_"):
            node.removeAttribute(key[5:-2])
            logging.getLogger('editor').info("attribute "+key[5:-2]+" of node "+str(node.id)+" removed")
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

    for key,value in attrs:
        if key in fieldnames:
            metafields[key] = formatdate(value, getFormat(fields, key))
        elif key in tattr.keys():
            technfields[key] = formatdate(value)
        else:
            obsoletefields[key] = value

    # remove all technical attributes
    if req.params.get("type","")=="technical":
        for key in technfields:
             node.removeAttribute(key)
        technfields = {}
        logging.getLogger('editor').info("technical attributes of node "+str(node.id)+" removed")

    req.writeTAL("web/edit/edit_admin.html", {"id":req.params.get("id","0"), "tab":req.params.get("tab", ""), "node":node, "obsoletefields":obsoletefields, "metafields":metafields, "fields":fields, "technfields":technfields, "tattr":tattr,"fd":formatdate, "gf":getFormat}, macro="edit_admin_file")

def getFormat(fields, name):
    for field in fields:
        if field.name == name:
            return field.getValues()


def formatdate(value, format=""):
    if format=="":
        format = '%d.%m.%Y %H:%M:%S'
    try:
        return format_date(parse_date(value,"%Y-%m-%dT%H:%M:%S"), format=format)
    except:
        return value