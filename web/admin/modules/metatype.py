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
import sys
import traceback
import core.tree as tree

from schema.schema import loadTypesFromDB
from core.datatypes import loadAllDatatypes
from web.admin.adminutils import Overview, getAdminStdVars
from core.tree import Node, getNode
from web.common.acl_web import makeList
from utils.utils import removeEmptyStrings 
from core.translation import lang, t
from schema.schema import getMetaFieldTypeNames, getMetaType, updateMetaType, existMetaType, deleteMetaType, fieldoption, moveMetaField, getMetaField, deleteMetaField, getFieldsForMeta, dateoption, requiredoption, existMetaField, updateMetaField, generateMask, cloneMask, exportMetaScheme, importMetaSchema
import re
import core.config as config


_masktypes = {"":"masktype_empty","edit":"masktype_edit", "search":"masktype_search", "shortview":"masktype_short", "fullview":"masktype_full"}

""" checks a string whether it only contains the alphanumeric chars as well as "-" """
def checkString(string):
    result = re.match("([\w\-]+)", string)
    if result != None and result.group(0) == string:
       return True
    return False


""" standard method for admin module """
def validate(req, op):
    path = req.path[1:].split("/")
    if len(path)==3 and path[2]=="overview":
        return showFieldOverview(req)

    if len(path)==4 and path[3]=="editor":
        return showEditor(req)

    if len(path)==2 and path[1]=="info":
        return showInfo(req)
    
    if "file" in req.params and req.params["file"].filesize>0:
        # import scheme from xml-file
        importfile = req.params.get("file")
        if importfile.tempname!="":
            xmlimport(req, importfile.tempname)
    
    try:
        if "detailof" in req.params.keys():
            req.params["detaillist_" + req.params["detailof"] + ".x"] = 1
        
        if "maskof" in req.params.keys() and req.params.get("form_op","")=="":
            req.params["masks_" + req.params["maskof"] + ".x"] = 1
        
        if "maskof" in req.params.keys() and req.params.get("form_op","")=="cancel":
            req.params["masks_"+ req.params["maskof"]+".x"] = 0

        for key in req.params.keys():
            # change field order up
            if key.startswith("updetail_"):
                moveMetaField(str(key[9:-2].split("|")[0]), str(key[9:-2].split("|")[1]), -1)
                req.params["detailof"] = str(key[9:-2].split("|")[0])
                return showDetailList(req, str(key[9:-2].split("|")[0]))

            # change field order down
            elif key.startswith("downdetail_"):
                moveMetaField(str(key[11:-2].split("|")[0]), str(key[11:-2].split("|")[1]), 1)
                req.params["detailof"] = str(key[11:-2].split("|")[0])
                return showDetailList(req, str(key[11:-2].split("|")[0]))

            # create new field
            elif key.startswith("newdetail_"):
                return FieldDetail(req, str(key[10:-2]), "")
                
            elif key.startswith("indexupdate_"):
                schema = tree.getNode(key[12:-2])
                s = schema.getAllItems()

                
                searchIndexer.updateNodes(schema.getAllItems())
                
                break
            
            elif key.startswith("editmask_"):
                return MaskDetails(req, key[9:-2].split("|")[0], key[9:-2].split("|")[1], err=0)

            elif key.startswith("masks_"):
                req.params["maskof"] = str(key[6:-2])
                return showMaskList(req, str(key[6:-2]))

            elif key.startswith("automask_"):
                mtype = getMetaType(str(key[9:-2]))
                generateMask(mtype)
                return showMaskList(req, str(key[9:-2]))

            elif key.startswith("newmask_"):
                return MaskDetails(req, key[8:-2].split("|")[0], "")

            elif key.startswith("deletemask_"):
                mtype = getMetaType(key[11:-2].split("|")[0])
                if key[11:-2].split("|")[1].isdigit():
                    mtype.removeChild(tree.getNode(key[11:-2].split("|")[1]))
                else:
                    mtype.removeChild(mtype.getMask(key[11:-2].split("|")[1]))
                return showMaskList(req, key[11:-2].split("|")[0])

            elif key.startswith("copymask_"):
                mtype = getMetaType(key[9:-2].split("|")[0])
                mask = mtype.getMask(key[9:-2].split("|")[1])
                cloneMask(mask, "copy_"+mask.getName())
                return showMaskList(req, key[9:-2].split("|")[0])

            # create new metadatatype
            elif key.startswith("new"):
                return MetatypeDetail(req, "")

            # edit metadatatype
            elif key.startswith("edit_"):
                return MetatypeDetail(req, str(key[5:-2]))

            # edit metadatafield: key[11:-2]= pid | id
            elif key.startswith("editdetail_"):
                return FieldDetail(req, str(key[11:-2].split("|")[0]), str(key[11:-2].split("|")[1]))
            
            # delete metadata
            elif key.startswith("delete_"):
                deleteMetaType(key[7:-2])
                break

            # delete metafield: key[13:-2] = pid | n
            elif key.startswith("deletedetail_"):
                deleteMetaField(key[13:-2].split("|")[0], key[13:-2].split("|")[1])
                req.params["detailof"] = key[13:-2].split("|")[0]
                return showDetailList(req, key[13:-2].split("|")[0])

            # show details for given metadatatype
            elif key.startswith("detaillist_"):
                req.params["detailof"] = str(key[11:-2])
                return showDetailList(req, str(key[11:-2]))

            elif key == "form_op":
                if req.params["form_op"] == "save_new":
                    # save metatype values
                    if str(req.params["mname"])=="" or str(req.params["mlongname"])=="" or req.params.get("mdatatypes","")=="":
                        return MetatypeDetail(req, "", 1) # no name was given
                        
                    elif existMetaType(req.params["mname"]):
                        return MetatypeDetail(req, "", 2) # metadata still existing
                    
                    elif checkString(str(req.params["mname"])) == False:
                         return MetatypeDetail(req, "", 4) # if the name contains wrong characters

                    else:
                        if "mactive" in req.params:
                            _active = 1
                        else:
                            _active = 0
                        updateMetaType(req.params["mname"], description=req.params["description"], longname=req.params["mlongname"], active=_active, datatypes=req.params["mdatatypes"].replace(";", ", "))

                        mtype = getMetaType(req.params["mname"])
                        mtype.setAccess("read", "")
                        for key in req.params.keys():
                            if key.startswith("left"):
                                mtype.setAccess(key[4:], req.params.get(key).replace(";",","))
                                break
                    break

                elif req.params["form_op"] == "save_edit":
                    # update metatype
                    if str(req.params["mname"])=="" or str(req.params["mlongname"])=="" or req.params.get("mdatatypes","")=="":
                        return MetatypeDetail(req, req.params["mname_orig"], 1) # no name was given
                        
                    elif req.params["mname_orig"] != req.params["mname"] and existMetaType(req.params["mname"]):
                        return MetatypeDetail(req, req.params["mname_orig"], 2) # metadata still existing

                    elif checkString(str(req.params["mname"])) == False:
                         return MetatypeDetail(req, req.params["mname_orig"], 4) # if the name contains wrong characters

                    else:
                        if "mactive" in req.params:
                            _active = 1
                        else:
                            _active = 0
                        updateMetaType(req.params["mname"], description=req.params["description"], longname=req.params["mlongname"], active=_active, datatypes=req.params["mdatatypes"].replace(";", ", "), orig_name=req.params["mname_orig"])
                        
                        mtype = getMetaType(req.params["mname"])
                        mtype.setAccess("read", "")
                        for key in req.params.keys():
                            if key.startswith("left"):
                                mtype.setAccess(key[4:], req.params.get(key).replace(";",","))
                                break
                    break

                elif req.params["form_op"] == "save_newdetail":
                    # save new metadatafield (detail)
                    if existMetaField(req.params["pid"], req.params["mname"]):
                        # field still existing
                        return FieldDetail(req, req.params["pid"], "", 3)
                        
                    elif req.params["mname"]=="" or req.params["mlabel"] == "":                            
                        return FieldDetail(req, req.params["pid"], "", 1)
                    elif checkString(req.params["mname"]) == False:
                         return FieldDetail(req, req.params["pid"], "", 4) # if the name contains wrong characters

                    else:
                        # save new field
                        try:
                            _option = ""
                            for key in req.params.keys():
                                if key.startswith("option_"):
                                    _option += key[7]
                        except:
                            _option = ""

                        _fieldvalue = ""
                        if 'mtype' in req.params.keys() and req.params.get('mtype') + "_value" in req.params.keys():
                            _fieldvalue = str(req.params[req.params['mtype'] + "_value"])
                        
                        updateMetaField(req.params["pid"], req.params["mname"], req.params["mlabel"], req.params["orderpos"], req.params["mtype"], _option, req.params["mdescription"], _fieldvalue, orig_name=req.params["mname"])
                        req.params["detailof"] = req.params["pid"]
                        return showDetailList(req, req.params["pid"])
                    break

                elif req.params["form_op"] == "save_editdetail":
                    # update metadatafield (detail)

                    if req.params["mname"]=="" or req.params["mlabel"] == "":
                        return FieldDetail(req, req.params["pid"], "", 1)

                    elif checkString(req.params["mname"]) == False:
                         return FieldDetail(req, req.params["pid"],"", 4) # if the name contains wrong characters
                    
                    else:
                        _len = 0
                        if req.params.get("mlength","").isdigit():
                            _len = int(req.params.get("mlength","0"))

                        try:
                            _option =""
                            for key in req.params.keys():
                                if key.startswith("option_"):
                                    _option += key[7]
                        except:
                            _option = ""

                        _fieldvalue = ""
                        if req.params.get('mtype','') + "_value" in req.params.keys():
                            _fieldvalue = str(req.params[req.params['mtype'] + "_value"])

                        updateMetaField(req.params["pid"], req.params["mname"], req.params["mlabel"], req.params["orderpos"], req.params["mtype"], _option, req.params["mdescription"], _fieldvalue, orig_name=req.params["mname_orig"])

                        req.params["detailof"] = req.params["pid"]
                        return showDetailList(req, req.params["pid"])
                    break

                elif req.params["form_op"]=="save_editmask":
                    if req.params["mname"]=="":
                        MaskDetails(req, req.params.get("mpid",""), req.params.get("morig_name",""), err=1)
                    elif checkString(req.params["mname"]) == False:
                         return MaskDetails(req, req.params.get("mpid",""), req.params.get("morig_name",""), err=4) # if the name contains wrong characters
                    else:
                        mtype = getMetaType(req.params.get("mpid",""))
                        mask = mtype.getMask(req.params.get("morig_name",""))
                        mask.setName(req.params.get("mname"))
                        mask.setDescription(req.params.get("mdescription"))
                        mask.setMasktype(req.params.get("mtype"))
                        mask.setLanguage(req.params.get("mlanguage", ""))
                        mask.setDefaultMask("mdefault" in req.params.keys())
                        return showMaskList(req, str(req.params.get("mpid","")))
                    operation += 1
                    break

                elif req.params["form_op"]=="save_newmask":

                    if req.params["mname"]=="":
                        return MaskDetails(req, req.params.get("mpid",""), "", err=1)
                    elif checkString(req.params["mname"]) == False:
                         return MaskDetails(req, req.params.get("mpid",""), req.params.get("morig_name",""), err=4) # if the name contains wrong characters
                    else:
                        mtype = getMetaType(req.params.get("mpid",""))
                        mask = tree.Node(req.params.get("mname",""), type="mask")
                        mask.setDescription(req.params.get("mdescription",""))
                        mask.set("type", "vgroup")
                        mask.setMasktype(req.params.get("mtype"))
                        mask.setLanguage(req.params.get("mlanguage", ""))
                        mask.setDefaultMask("mdefault" in req.params.keys())
                        mtype.addChild(mask)

                        return showMaskList(req, str(req.params.get("mpid","")))
        
        return view(req)
    except:
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])

""" show all defined metadatatypes """
def view(req):
    mtypes = loadTypesFromDB()
    pages = Overview(req, mtypes)
    order = req.params.get("order", "")
    
    # sorting
    if order != "":
        if int(order[0:1])==0:
            mtypes.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))
        elif int(order[0:1])==1:
            mtypes.sort(lambda x, y: cmp(x.getLongName().lower(),y.getLongName().lower()))
        elif int(order[0:1])==2:
            mtypes.sort(lambda x, y: cmp(x.getDescription().lower(),y.getDescription().lower()))
        elif int(order[0:1])==3:
            mtypes.sort(lambda x, y: cmp(x.getActive(),y.getActive()))
        elif int(order[0:1])==4:
            mtypes.sort(lambda x, y: cmp(x.getDatatypeString().lower(),y.getDatatypeString().lower()))
        elif int(order[0:1])==5:
            mtypes.sort(lambda x, y: cmp(x.metadatatype.getAccess("read"),y.metadatatype.getAccess("read")))
        elif int(order[0:1])==6:
            mtypes.sort(lambda x, y: cmp(x.searchIndexCorrupt(),y.searchIndexCorrupt()))
        elif int(order[0:1])==7:
            mtypes.sort(lambda x, y: cmp(len(x.getAllItems()),len(y.getAllItems())))
        if int(order[1:])==1:
            mtypes.reverse()
    else:
        mtypes.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req),"admin_meta_col_1"),t(lang(req),"admin_meta_col_2"),t(lang(req),"admin_meta_col_3"),t(lang(req),"admin_meta_col_4"),t(lang(req),"admin_meta_col_5"),t(lang(req),"admin_meta_col_6"),t(lang(req),"admin_meta_col_7"), t(lang(req),"admin_meta_col_8")])
    v["metadatatypes"] = mtypes
    v["datatypes"] = loadAllDatatypes()
    v["pages"] = pages
    return req.getTAL("web/admin/modules/metatype.html", v, macro="view_type")
    
""" form for metadata (edit/new) """
def MetatypeDetail(req, id, err=0):
    v = getAdminStdVars(req)
        
    if err==0 and id=="":
        # new metadatatype
        metadatatype = tree.Node("", type="metadatatype")
        v["original_name"] = ""
        
    elif id!="" and err==0:
        # edit metadatatype
        metadatatype = getMetaType(id)
        v["original_name"] = metadatatype.getName()
       
    else:
        # error   
        metadatatype = tree.Node(req.params["mname"], type="metadatatype")
        metadatatype.setDescription(req.params["description"])
        metadatatype.setLongName(req.params["mlongname"])
        metadatatype.setActive("mactive" in req.params)
        metadatatype.setDatatypeString(req.params.get("mdatatypes","").replace(";",", "))

        v["original_name"] = req.params["mname_orig"]

    v["datatypes"] = loadAllDatatypes()
    v["metadatatype"] = metadatatype
    v["error"] = err
    
    rule = metadatatype.getAccess("read")
    if rule:
        rule = rule.split(",")
    else:
        rule = []
    
    rights = removeEmptyStrings(rule)
    v["acl"] =  makeList(req, "read", rights, {}, overload=0, type="read")

    return req.getTAL("web/admin/modules/metatype.html", v, macro="modify_type")
   
""" list all fields of given metadatatype """
def showDetailList(req, id):
    global fieldoption

    metadatatype = getMetaType(id)
    metafields = metadatatype.getMetaFields()
    pages = Overview(req, metafields)
    order = req.params.get("order","")

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
    v["sortcol"] = pages.OrderColHeader(["", t(lang(req),"admin_metafield_col_1"),t(lang(req),"admin_metafield_col_2"),t(lang(req),"admin_metafield_col_3")])
    v["metadatatype"] = metadatatype
    v["metafields"] = metafields
    v["fieldoptions"] = fieldoption
    v["fieldtypes"] = getMetaFieldTypeNames()
    v["pages"] = pages
    v["order"] = order
    return req.getTAL("web/admin/modules/metatype.html", v, macro="view_field")

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
        
        field = tree.Node(req.params["mname"], type="metafield")
        field.setLabel(req.params["mlabel"])
        field.setOrderPos(req.params["orderpos"])
        field.setFieldtype(req.params["mtype"])
        field.setOption(_option)
        field.setValues(_fieldvalue)
        field.setDescription(req.params["mdescription"])

    attr = {}
    metadatatype = getMetaType(pid)
    for t in metadatatype.getDatatypes():
        node = Node(type=t)
        attr.update(node.getTechnAttributes())

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

    v["icons"] = {"externer Link":"/img/extlink.png", "Email":"/img/email.png"}
    v["valuelist"] = ("", "", "")
    if field.getFieldtype()=="url":
        v["valuelist"] = field.getValueList()
        while len(v["valuelist"])!=3:
            v["valuelist"].append("")
    return req.getTAL("web/admin/modules/metatype.html", v, macro="modify_field")

""" mask overview """
def showMaskList(req, id):
    global fieldoption, _masktypes

    metadatatype = getMetaType(id)
    masks = metadatatype.getMasks()
    pages = Overview(req, masks)
    order = req.params.get("order","")
    
    defaults = {}
    for mask in masks:
        if mask.getDefaultMask():
            defaults[mask.getMasktype()] = mask.id

    # sorting
    if order != "":
        if int(order[0:1])==0:
            masks.sort(lambda x, y: cmp(x.getName().lower(),y.getName().lower()))    
        elif int(order[0:1])==1:
            masks.sort(lambda x, y: cmp(x.getMasktype(),y.getMasktype()))
        elif int(order[0:1])==2:
            masks.sort(lambda x, y: cmp(x.getDescription(),y.getDescription()))
        elif int(order[0:1])==3:
            masks.sort(lambda x, y: cmp(x.getDefaultMask(),y.getDefaultMask()))
        elif int(order[0:1])==4:
            masks.sort(lambda x, y: cmp(x.getLanguage(),y.getLanguage()))
        if int(order[1:])==1:
            masks.reverse()
    else:
        masks.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req),"admin_mask_col_1"),t(lang(req),"admin_mask_col_2"),t(lang(req),"admin_mask_col_3"),t(lang(req),"admin_mask_col_4"),t(lang(req),"admin_mask_col_5")])
    v["metadatatype"] = metadatatype
    v["masktypes"] = _masktypes
    v["lang_icons"] = {"de":"/img/flag_de.gif", "en":"/img/flag_en.gif", "no":"/img/emtyDot1Pix.gif"}
    v["masks"] = masks
    v["pages"] = pages
    v["order"] = order
    v["defaults"] = defaults
    return req.getTAL("web/admin/modules/metatype.html", v, macro="view_mask")

""" mask details """
def MaskDetails(req, pid, id, err=0):
    global _masktypes
    mtype = getMetaType(pid)

    if err==0 and id=="":
        # new mask
        mask = tree.Node("", type="mask")

    elif id!="" and err==0:
        # edit mask
        if id.isdigit():
            mask = tree.getNode(id)
        else:
            mask = mtype.getMask(id)

    else:
        # error filling values
        mask = tree.Node(req.params.get("mname",""), type="mask")
        mask.setDescription(req.params.get("mdescription",""))
        mask.setMasktype(req.params.get("mtype"))
        mask.setLanguage(req.params.get("mlanguage", ""))
        mask.setDefaultMask(req.params.get("mdefault", False))
        
    v = getAdminStdVars(req)
    v["mask"] = mask
    v["mtype"] = mtype
    v["error"] = err
    v["pid"] = pid
    v["masktypes"] = _masktypes
    v["id"] = id
    v["langs"] = config.get("i18n.languages").split(",")

    return req.getTAL("web/admin/modules/metatype.html", v, macro="modify_mask")

""" popup info form """
def showInfo(req):
    return req.getTAL("web/admin/modules/metatype.html", {"fieldtypes":getMetaFieldTypeNames()}, macro="show_info")

""" popup form with field definition """
def showFieldOverview(req):
    global fieldoption
    path = req.path[1:].split("/")
    fields = getFieldsForMeta(path[1])
    fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
    
    v = {}
    v["metadatatype"] = getMetaType(path[1])
    v["metafields"] = fields
    v["fieldoptions"] = fieldoption
    v["fieldtypes"] = getMetaFieldTypeNames()

    return req.getTAL("web/admin/modules/metatype.html", v, macro="show_fieldoverview")

""" export metadatatype-definition (XML) """
def export(req, name):
    return exportMetaScheme(name)

""" import definition from file """
def xmlimport(req, filename):
    importMetaSchema(filename)
       
def showEditor(req):
    path = req.path[1:].split("/")
    mtype = getMetaType(path[1])
    editor = mtype.getMask(path[2])

    req.params["metadatatype"] = mtype
    for key in req.params.keys():
        if req.params.get("op","")=="cancel":
            if "savedetail" in req.params.keys():
                del req.params["savedetail"]
            break

        if key.startswith("up_"):
            changeOrder(tree.getNode(key[3:-2]).getParents()[0], tree.getNode(key[3:-2]).getOrderPos(), -1)
            break
     
        if key.startswith("down_"):
            changeOrder(tree.getNode(key[5:-2]).getParents()[0], -1, tree.getNode(key[5:-2]).getOrderPos())
            break

        if key.startswith("delete_"):
            editor.deleteMaskitem(key[7:-2])
            break

        if key.startswith("edit_"):
            op = key[5:-2]
            req.params["edit"] = op
            req.params["op"] = "edit"
            break

        if key.startswith("new_"):
            req.params["edit"] = " "
            break

        if key.startswith("newdetail_"):
            req.params["pid"] = key[10:-2]
            req.params["op"] = "newdetail"
            req.params["edit"] = " "
            if req.params.get("type")in("vgroup","hgroup"):
                req.params["type"] = "field"
                req.params["op"] = "new"
            if "savedetail" in req.params.keys():
                del req.params["savedetail"]
            break

    if req.params.get("op","")=="group":
        # create new group for selected objects
        req.params["op"] = "new"
        req.params["edit"] = " "
        req.params["type"] = req.params.get("group_type")
        req.params["pid"] = getNode(req.params.get("sel_id").split(";")[0]).getParents()[0].id
 
    if "saveedit" in req.params.keys() and req.params.get("op","")!="cancel":
        # update node
        label = req.params.get("label","-new-")
        if req.params.get("op", "")=="edit":
            item = tree.getNode(req.params.get("id"))
            item.setLabel(req.params.get("label", ""))
            
            field = item.getChildren()
            try:
                field = list(field)[0]
                if str(field.id)!=str(req.params.get("field")):
                    item.removeChild(field)
                    item.addChild(tree.getNode(long(req.params.get("field"))))

                field.setValues(req.params.get(field.get("type")+"_value",""))
            except:
                pass

        elif req.params.get("op", "")=="new":
            if req.params.get("fieldtype","")=="common":
                # existing field used
                fieldid = long(req.params.get("field"))
            else:
                # create new metaattribute
                parent = req.params.get("metadatatype").getName()
                fieldvalue = req.params.get(req.params.get("newfieldtype","")+'_value',"")
                
                if req.params.get("type")=="label":
                    # new label
                    fieldid = ""
                else:
                    # normal field
                    updateMetaField(parent, req.params.get("fieldname"), label, 0, req.params.get("newfieldtype"), option="", description=req.params.get("description",""), fieldvalues=fieldvalue, fieldvaluenum="", orig_name="")
                    fieldid = str(getMetaField(parent, req.params.get("fieldname")).id)
            
            item = editor.addMaskitem( label, req.params.get("type"), fieldid, req.params.get("pid","0") )

            position = req.params.get("insertposition", "end")
            if position=="end":
                # insert at the end of existing mask
                item.setOrderPos(len(tree.getNode(req.params.get("pid")).getChildren())-1)
            else:
                # insert at special position
                fields = editor.getMaskFields()
                fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
                for f in fields:
                    if f.getOrderPos()>=tree.getNode(position).getOrderPos() and f.id!=item.id:
                        f.setOrderPos(f.getOrderPos()+1)               
                item.setOrderPos(tree.getNode(position).getOrderPos()-1)

        item.setWidth(int(req.params.get("width", 400)))
        item.setUnit(req.params.get("unit", ""))
        item.setDefault(req.params.get("default", ""))   
        item.setDescription(req.params.get("description",""))
        if "required" in req.params.keys():
            item.setRequired(1)
        else:
            item.setRequired(0)

    if "savedetail" in req.params.keys():
        label = req.params.get("label","-new-")
        # save details (used for hgroup)
        if req.params.get("op","")=="edit":
            item = tree.getNode(req.params.get("id"))
            item.setLabel(req.params.get("label", ""))
        elif req.params.get("op", "")=="new":
            if req.params.get("sel_id","")!="":
                item = editor.addMaskitem( label, req.params.get("type"), req.params.get("sel_id","")[:-1], long(req.params.get("pid","0")) )
            else:
                item = editor.addMaskitem( label, req.params.get("type"), 0, long(req.params.get("pid","0")) )

        # move selected elementd to new item-container
        if req.params.get("sel_id","")!="":
            pos = 0
            for i in req.params.get("sel_id")[:-1].split(";"):
                n = getNode(i) # node to move
                n.setOrderPos(pos)
                p = getNode(n.getParents()[0].id) # parentnode
                p.removeChild(n)
                item.addChild(n) # new group
                pos += 1

        # position:
        position = req.params.get("insertposition", "end")
        if position=="end":
            # insert at the end of existing mask
            item.setOrderPos(len(tree.getNode(req.params.get("pid")).getChildren())-1)
        else:
            # insert at special position
            fields = []
            pidnode = getNode(req.params.get("pid"))
            for field in pidnode.getChildren():
                if field.getType().getName()=="maskitem" and field.id!=pidnode.id:
                    fields.append(field)
            fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
            for f in fields:
                if f.getOrderPos()>=tree.getNode(position).getOrderPos() and f.id!=item.id:
                    f.setOrderPos(f.getOrderPos()+1)
            item.setOrderPos(tree.getNode(position).getOrderPos()-1)

        if "edit" not in req.params.keys():
            item.set("type", req.params.get("type",""))
        item.setWidth(int(req.params.get("width", 400)))
        item.setUnit(req.params.get("unit", ""))
        item.setDefault(req.params.get("default", ""))
        item.setDescription(req.params.get("description",""))
        if "required" in req.params.keys():
            item.setRequired(1)
        else:
            item.setRequired(0)
    
    v= {}
    v["edit"] = req.params.get("edit","")
    if req.params.get("edit","")!="":
        v["editor"] = editor.editItem(req)
    else:
        # show metaEditor
        v["editor"] = req.getTALstr(editor.getMetaMask(language=lang(req)), {})

    return req.getTAL("web/admin/modules/metatype.html", v, macro="editor_popup")


def changeOrder(parent, up, down):
    """ change order of given nodes """
    i = 0
    for child in parent.getChildren().sort():
        try:
            if i == up:
                pos = i-1
            elif i == up-1:
                pos = up
            elif i == down:
                pos = i+1
            elif i == down+1:
                pos = down
            else:
                pos = i
            child.setOrderPos(pos)
            i = i + 1
        except:
            pass

