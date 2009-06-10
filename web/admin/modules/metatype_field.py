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

import re
import core.tree as tree

from web.admin.adminutils import Overview, getAdminStdVars, getSortCol, getFilter
from schema.schema import getMetaType, fieldoption, getMetaFieldTypeNames, getMetaField, getFieldsForMeta, dateoption, requiredoption
from core.translation import lang, t
from core.tree import Node


""" list all fields of given metadatatype """
def showDetailList(req, id):
    global fieldoption
    metadatatype = getMetaType(id)
    metafields = metadatatype.getMetaFields()
    
    order = getSortCol(req)
    actfilter = getFilter(req)

    # filter
    if actfilter!="":
        if actfilter in ("all", "*", t(lang(req),"admin_filter_all")):
            None # all users
        elif actfilter=="0-9":
            num = re.compile(r'([0-9])')
            if req.params.get("filtertype","")=="name":
                metafields = filter(lambda x: num.match(x.getName()), metafields)
            else:
                metafields = filter(lambda x: num.match(x.getLabel()), metafields)
            
        elif actfilter=="else" or actfilter==t(lang(req),"admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9]|\.)')
            if req.params.get("filtertype","")=="name":
                metafields = filter(lambda x: not all.match(x.getName()), metafields)
            else:
                metafields = filter(lambda x: not all.match(x.getLabel()), metafields)
        else:
            if req.params.get("filtertype","")=="name":
                metafields = filter(lambda x: x.getName().lower().startswith(actfilter), metafields)
            else:
                metafields = filter(lambda x: x.getLabel().lower().startswith(actfilter), metafields)
            
    pages = Overview(req, metafields)
    
    # sorting
    if order != "":
        if int(order[0:1])==0:
            metafields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
        elif int(order[0:1])==1:
            metafields.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))    
        elif int(order[0:1])==2:
            metafields.sort(lambda x, y: cmp(x.getLabel().lower(),y.getLabel().lower()))
        elif int(order[0:1])==3:
            metafields.sort(lambda x, y: cmp(getMetaFieldTypeNames()[str(x.getFieldtype())],getMetaFieldTypeNames()[str(y.getFieldtype())]))
        if int(order[1:])==1:
            metafields.reverse()
    else:
        metafields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))

    v = getAdminStdVars(req)
    v["filterattrs"] = [("name","admin_metafield_filter_name"),("label","admin_metafield_filter_label")]
    v["filterarg"] = req.params.get("filtertype", "name")
    
    v["sortcol"] = pages.OrderColHeader(["", t(lang(req),"admin_metafield_col_1"),t(lang(req),"admin_metafield_col_2"),t(lang(req),"admin_metafield_col_3")])
    v["metadatatype"] = metadatatype
    v["metafields"] = metafields
    v["fieldoptions"] = fieldoption
    v["fieldtypes"] = getMetaFieldTypeNames()
    v["pages"] = pages
    v["order"] = order
    v["actfilter"] = actfilter
    
    v["actpage"] = req.params.get("actpage")
    if str(req.params.get("page","")).isdigit():
        v["actpage"] = req.params.get("page")
    
        
    return req.getTAL("web/admin/modules/metatype_field.html", v, macro="view_field")
    
    
    
""" form for field of given metadatatype (edit/new) """
def FieldDetail(req, pid, id, err=0):
    global dateoption, requiredoption, fieldoption

    _option =""
    for key in req.params.keys():
        if key.startswith("option_"):
            _option += key[7]

    if err==0 and id=="":
        # new field
        field = tree.Node("", type="metafield")

    elif id!="":
        # edit field
        field = getMetaField(pid, id)
         
    else:
        # error filling values
        _fieldvalue = ""
        if req.params.get('mtype','') + "_value" in req.params.keys():
            _fieldvalue = str(req.params[req.params.get('mtype','') + "_value"])
        
        if (req.params.get("mname")==""):
            field = tree.Node(req.params.get("orig_name"), type="metafield")
        else:
             field = tree.Node(req.params.get("mname"), type="metafield")
        field.setLabel(req.params.get("mlabel"))
        field.setOrderPos(req.params.get("orderpos"))
        field.setFieldtype(req.params.get("mtype"))
        field.setOption(_option)
        field.setValues(_fieldvalue)
        field.setDescription(req.params.get("mdescription"))

    attr = {}
    metadatatype = getMetaType(pid)
    for t in metadatatype.getDatatypes():
        node = tree.Node(type=t)
        try:
            attr.update(node.getTechnAttributes())
        except AttributeError:
            continue

    metafields = {}
    for fields in getFieldsForMeta(pid):
        if fields.getType()!="union":
            metafields[fields.getName()] = fields

    v = getAdminStdVars(req)
    v["metadatatype"] = metadatatype
    v["metafield"] = field
    v["error"] = err
    v["fieldtypes"] = getMetaFieldTypeNames()
    v["dateoptions"] = dateoption
    v["datatypes"] = attr
    v["requiredoptions"] = requiredoption
    v["fieldoptions"] = fieldoption
    v["metafields"] = metafields
    v["filtertype"] = req.params.get("filtertype","")
    v["actpage"] = req.params.get("actpage")

    v["icons"] = {"externer Link":"/img/extlink.png", "Email":"/img/email.png"}
    v["url_targets"] = {"selbes Fenster":"same", "neues Fenster":"_blank"}
    v["valuelist"] = ("", "", "", "")
    if field.getFieldtype()=="url":
        v["valuelist"] = field.getValueList()
        while len(v["valuelist"])!=4:
            v["valuelist"].append("")
    return req.getTAL("web/admin/modules/metatype_field.html", v, macro="modify_field")
    