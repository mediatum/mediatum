# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

import schema.searchmask as searchmask
from core.users import user_from_session as _user_from_session
from core import httpstatus
import json
from core import Node
from core import db
import core.nodecache as _nodecache
from core.systemtypes import Searchmasks

q = db.query

def getContent(req, ids):
    user = _user_from_session()
    node = q(Node).get(ids[0])

    if not node.has_write_access() or "searchmask" in user.hidden_edit_functions:
        req.response.status_code = httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    p2 = {}
    for k, v in req.params.items():
        if k.endswith(".x") or k.endswith(".y"):
            p2[k[:-2]] = v
        else:
            p2[k] = v
    req.params = p2

    openfield = None
    delfield = None
    delsubfield = None
    for k, v in req.params.items():
        if k.startswith("open_"):
            openfield = k[5:]
        if k.startswith("del_"):
            delfield = k[4:]
        if k.startswith("delsub_"):
            delsubfield = k[7:]

    searchtype = req.params.get("searchtype", None)
    if not searchtype:
        searchtype = node.get("searchtype")
        if not searchtype:
            searchtype = "none"
            # if a parent has a search mask, use 'inherit'
            n = node
            while len(n.parents):
                n = n.parents[0]
                if n.get("searchtype") == "own":
                    searchtype = "parent"
    node.set("searchtype", searchtype)

    schema = req.params.get("schema", None)
    schemafield = req.params.get("schemafield", None)
    selectedfieldid = req.params.get("selectedfield", None)
    if schema:
        if schema.endswith(";"):
            schema = schema[:-1]
        schema = q(Node).get(schema)
        if not isinstance(schema, Node):
            schema = None

    if schemafield:
        if schemafield.endswith(";"):
            schemafield = schemafield[:-1]
        schemafield = q(Node).get(schemafield)
        if not isinstance(schemafield, Node):
            schemafield = None

    if schema and schemafield and schemafield not in schema.children:
        schemafield = None
    if schemafield and schemafield.type != "metafield":
        schemafield = None

    fields = None
    selectedfield = None
    isnewfield = False
    createsub = False
    closefield = False

    if searchtype == "own":
        maskname = node.get("searchmaskname")

        mask = q(Searchmasks).one().children.filter_by(name=maskname).scalar()
        if not maskname or mask is None:
            mask = searchmask.generateMask(node)

        if selectedfieldid:  # edit
            selectedfield = q(Node).get(selectedfieldid)
            assert selectedfield in mask.children
            selectedfield.name = req.params["fieldname"]
            if "createsub" in req.params and schemafield:
                createsub = True
                selectedfield.children.append(schemafield)
            if delsubfield:
                selectedfield.children.remove(q(Node).get(delsubfield))

        if req.params.get("isnewfield", "") == "yes":  # create a new field
            isnewfield = True
            l = mask.children.count()
            mask.children.append(Node("Suchfeld %s" % l, "searchmaskitem"))

        elif delfield:  # del a field
            delfield = q(Node).get(delfield)
            assert delfield in mask.children
            mask.children.remove(delfield)

        elif openfield:  # unfold a new field
            selectedfieldid = openfield

        elif "close" in req.params:  # fold a field
            closefield = True
            selectedfieldid = None

        if selectedfieldid:
            selectedfield = q(Node).get(selectedfieldid)
            if selectedfield not in mask.children:  # this usually happens if the field was just deleted
                selectedfield = None
        else:
            selectedfield = None

        fields = mask.children.all()
    db.session.commit()

    data = dict(
            idstr=",".join(ids),
            node=node,
            searchtype=searchtype,
            schemas=_nodecache.get_metadatatypes_node().children.sort_by_name().all(),
            searchfields=fields,
            selectedfield=selectedfield,
            newfieldlink="edit_content?srcnodeid={nid}&id={nid}&tab=searchmask".format(nid=node.id),
            defaultschemaid=None,
            defaultfieldid=None,
            id=req.params.get("id"),
        )

    if schema:
        data["defaultschemaid"] = schema.id
    if schemafield:
        data["defaultfieldid"] = schemafield.id

    data["schema"] = schema

    def display(schemafield):
        if not schemafield or schemafield.type != 'metafield':
            return 0
        if not schemafield.Searchfield():
            return 0
        return 1
    data["display"] = display
    data["csrf"] = req.csrf_token.current_token
    searchtypechanged = False
    if req.params.get("searchtypechanged", "") == "true":
        searchtypechanged = True

    if any([openfield, isnewfield, delfield, delsubfield, createsub, schema, searchtypechanged, closefield]):
        content =  _tal.processTAL(data, file="web/edit/modules/searchmask.html", macro="edit_search", request=req)
        s = json.dumps({'content': content}, ensure_ascii=False)
        req.response.set_data(s)
        return None

    return _tal.processTAL(data, file="web/edit/modules/searchmask.html", macro="edit_search", request=req)
