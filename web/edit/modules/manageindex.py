"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <seiferta@in.tum.de>

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


import mediatumtal.tal as _tal
from schema.schema import loadTypesFromDB, getMetaType, get_permitted_schemas
from utils.utils import u, suppress
from contenttypes import Data
from core import Node
from core import db
from utils.pathutils import getPaths
from sqlalchemy import and_

q = db.query

def getInformation():
    return {"version": "1.0", "system": 0}

def getAllAttributeValues(attribute, schema):
    values = {}
    nids_values = q(Node.id, Node.a[attribute]).filter(Node.schema == schema).filter(
        Node.a[attribute] != None and Node.a[attribute] != '').distinct(Node.a[attribute]).all()
    for nid, value in nids_values:
        for s in value.split(";"):
            s = u(s.strip())
            if s not in values:
                values[s] = []
            values[s].append(nid)
    return values


def replaceValue(value, oldvalue, replacement):
    ret = []
    for val in value.split(";"):
        if val.strip() == oldvalue.strip():
            ret.append(replacement)
        else:
            ret.append(val)
    return ";".join(ret)


def getContent(req, ids):

    def getSchemes(req):
        schemes = AccessData(req).filter(loadTypesFromDB())
        return filter(lambda x: x.isActive(), schemes)

    ret = ""
    v = {"message": ""}

    if len(ids) >= 0:
        ids = ids[0]

    v["id"] = ids

    if "do_action" in req.params.keys():  # process nodes
        fieldname = req.params.get("fields")
        old_values = u(req.params.get("old_values", "")).split(";")
        new_value = u(req.params.get("new_value"))
        basenode = q(Node).get(ids)
        entries = getAllAttributeValues(fieldname, req.params.get("schema"))

        c = 0
        for old_val in old_values:
            for n in AccessData(req).filter(q(Node).filter(Node.id.in_(entries[old_val])).all()):
                with suppress(Exception, warn=False):
                    n.set(fieldname, replaceValue(n.get(fieldname), u(old_val), u(new_value)))
                    c += 1
        v["message"] = _tal.processTAL({"number": c}, file="web/edit/modules/manageindex.html", macro="operationinfo", request=req)

    if "style" in req.params.keys():  # load schemes
        if req.params.get("action", "") == "schemes":
            v["schemes"] = getSchemes(req)
            req.response.set_data(_tal.processTAL(v, file="web/edit/modules/manageindex.html", macro="schemes_dropdown", request=req))
            return ""

        elif req.params.get("action", "").startswith("indexfields__"):  # load index fields
            schema = getMetaType(req.params.get("action", "")[13:])
            fields = []
            for field in schema.getMetaFields():
                if field.getFieldtype() == "ilist":
                    fields.append(field)
            v["fields"] = fields
            v["schemaname"] = schema.getName()
            req.response.set_data(_tal.processTAL(v, file="web/edit/modules/manageindex.html", macro="fields_dropdown", request=req))
            return ""

        elif req.params.get("action", "").startswith("indexvalues__"):  # load values of selected indexfield
            node = q(Node).get(ids)
            fieldname = req.params.get("action").split("__")[-2]
            schema = req.params.get("action").split("__")[-1]
            v["entries"] = []
            if node:
                v["entries"] = getAllAttributeValues(fieldname, schema)
                v["keys"] = v["entries"].keys()
                v["keys"].sort(lambda x, y: cmp(x.lower(), y.lower()))
            req.response.set_data(_tal.processTAL(v, file="web/edit/modules/manageindex.html", macro="fieldvalues", request=req))
            return ""

        elif req.params.get("action", "").startswith("children__"):  # search for children of current collection
            scheme = req.params.get("action", "").split("__")[1]
            fieldname = req.params.get("action", "").split("__")[2]
            values = req.params.get("action", "").split("__")[3].split(";")[:-1]
            all_values = getAllAttributeValues(fieldname, scheme)

            def isChildOf(access, node, basenodeid):
                for ls in getPaths(node):
                    if basenodeid in [unicode(n.id) for n in ls]:
                        return 1
                return 0

            subitems = {}
            for value in values:
                value = u(value)
                if value in all_values:
                    subitems[value] = []
                    for l in all_values[value]:
                        if isChildOf(AccessData(req), q(Node).get(l), ids):
                            subitems[value].append(l)

            v["items"] = subitems
            v["keys"] = subitems.keys()
            v["keys"].sort()
            req.response.set_data(_tal.processTAL(v, file="web/edit/modules/manageindex.html", macro="valueinfo", request=req))
            return ""

    else:
        v["csrf"] = req.csrf_token.current_token
        return _tal.processTAL(v, file="web/edit/modules/manageindex.html", macro="manageform", request=req)
