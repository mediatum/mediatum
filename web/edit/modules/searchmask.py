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

import schema.schema as schema
import schema.searchmask as searchmask
import core.users as users
from core.acl import AccessData
from core.transition import httpstatus
from core import Node
from core import db
from core.systemtypes import Searchmasks

q = db.query

def getContent(req, ids):
    user = users.getUserFromRequest(req)
    node = q(Node).get(ids[0])
    access = AccessData(req)
    
    if not access.hasWriteAccess(node) or "searchmask" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

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

    root = q(Searchmasks).one()

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

    myschema = q(Node).get(req.params.get("schema", None))
    if not isinstance(myschema, Node):
        myschema = None

    schemafield = q(Node).get(req.params.get("schemafield", None))
    if not isinstance(schemafield, Node):
        schemafield = None

    if myschema and schemafield and schemafield not in myschema.children:
        schemafield = None
    if schemafield and schemafield.type != "metafield":
        schemafield = None
   
    fields = None
    selectedfield = None

    if searchtype == "own":
        maskname = node.get("searchmaskname")

        #todo: hasChild doesnt exist
        if not maskname or root.hasChild(maskname) == 0:
            mask = searchmask.generateMask(node)
        else:
            mask = root.getChild(maskname)
        
        selectedfieldid = req.params.get("selectedfield", None)
        if selectedfieldid:  # edit
            selectedfield = q(Node).get(selectedfieldid)
            assert selectedfield in mask.children
            selectedfield.setName(req.params["fieldname"])
            if "createsub" in req.params and schemafield:
                selectedfield.children.append(schemafield)
            if delsubfield:
                selectedfield.children.remove(q(Node).get(delsubfield))

        if req.params.get("isnewfield", "") == "yes":  # create a new field
            #todo:getNumChildren doesnt exist
            l = mask.getNumChildren()
            mask.children.append(Node("Suchfeld %s" % l, "searchmaskitem"))

        elif delfield:  # del a field
            delfield = q(Node).get(delfield)
            assert delfield in mask.children
            mask.children.remove(delfield)

        elif openfield:  # unfold a new field
            selectedfieldid = openfield

        elif "close" in req.params:  # fold a field
            selectedfieldid = None

        if selectedfieldid:
            selectedfield = q(Node).get(selectedfieldid)
            if selectedfield not in mask.children:  # this usually happens if the field was just deleted
                selectedfield = None
        else:
            selectedfield = None

        if mask is None:
            print "no parent searchmask found, empty mask created"
            mask = Node(maskname, "searchmask")

        fields = mask.children

    db.session.commit()

    data = {"idstr": ",".join(ids),
            "node": node,
            "searchtype": searchtype,
            "schemas": schema.loadTypesFromDB(),
            "searchfields": fields,
            "selectedfield": selectedfield,
            "newfieldlink": "edit_content?id=%s&tab=searchmask" % node.id,
            "defaultschemaid": None,
            "defaultfieldid": None}

    if myschema:
        data["defaultschemaid"] = myschema.id
    if schemafield:
        data["defaultfieldid"] = schemafield.id

    data["schema"] = myschema

    def display(schemafield): 
        if not schemafield or schemafield.type != 'metafield':
            return 0
        if not schemafield.Searchfield():
            return 0
        if schemafield.get('type') == 'union':
            return 0
        return 1
    data["display"] = display

    return req.getTAL("web/edit/modules/searchmask.html", data, macro="edit_search")
