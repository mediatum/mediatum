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
import os
from utils import *
import core.tree
import logging
import core.config
import sys, types
import traceback
import utils.dicts
from core.translation import *

from metadatatypes import *
from date import validateDateString


log = logging.getLogger('backend')

#
# metadatatype
#
class Metadatatype(tree.Node):
        
    def getName(self):
        return self.get("name")
    def setName(self, value):
        self.set("mame", value)

    def getDescription(self):
        return self.get("description")
    def setDescription(self, value):
        self.set("description", value)

    def getLongName(self):
        return self.get("longname")
    def setLongName(self, value):
        self.set("longname", value)

    def getActive(self):
        if self.get("active"):
            return int(self.get("active"))
        else:
            return 0
    def setActive(self, value):
        if value:
            self.set("active", "1")
        else:
            self.set("active", "0")
    
    def isActive(self):
        if self.getActive()==0:
            return False
        return True
        
    def getDatatypes(self):
        return self.get("datatypes").split(", ")
    def setDatatype(self, valuelist):
        self.set("datatypes", ", ".join(["%s" %k for k in valuelist]))
 
    def getDatatypeString(self):
        return self.get("datatypes")
    def setDatatypeString(self, value):
        self.set("datatypes", str(value))
   
    def getNumFields(self):
        return len(self.getMetaFields())
        
    def getNumNodes(self):
        return getNumberNodes(self.name)

    def getMetaFields(self,type=None):
        fields = []
        for item in self.getChildren().sort():
            if item.getTypeName()=="metafield":
                if not type or type in item.getOption():
                    fields.append(item)
        return fields

    def getMetaField(self, name):
        try:
            return self.getChild(name)
        except tree.NoSuchNodeError:
            print "metadatafield '" + str(name) + "' not found"
            return None

    def getMasks(self):
        masks = []
        for item in self.getChildren().sort():
            if item.getTypeName()=="mask":
                masks.append(item)
        return masks

    def getMask(self, name):
        try:
            return self.getChild(name)
        except tree.NoSuchNodeError:
            print "mask '" + str(name) + "' not found"
            return None
          
    def hasUploadForm(self):
        global nodeclasses
        for dtype in self.getDatatypes():
            obj = nodeclasses[dtype]
            if "upload_form" in obj.__dict__:
                return True
        return False

class Mask(tree.Node):

    def getFormHTML(self, nodes, req):
        if not self.getChildren():
            return None
        
        ret = ''
        for field in self.getChildren().sort():
            element = field.getField()
            t = getMetadataType(field.get("type"))
            ret += t.getFormHTML(field, nodes, req)
        return ret


    def getViewHTML(self, nodes, flags=0, language=None):
        if not self.getChildren():
            return []
        if flags & 4:
            ret = []
        else:
            ret = ''
        for field in self.getChildren().sort():
            t = getMetadataType(field.get("type"))
            if flags & 4: # data mode
                v = t.getViewHTML(field, nodes, flags, language=language)
                if flags & 2:   # hide empty
                    if v[1].strip()!="":
                        ret.append(v)
                else:
                    ret.append(v)
            else:
                ret += t.getViewHTML(field, nodes, flags, language=language)
        return ret


    def getViewList(self, node, flags=0, language=None):
        if not self.getChildren():
            return None
        if flags & 4:
            ret = []
        else:
            ret = ''
        for field in self.getChildren().sort():
            t = getMetadataType(field.get("type"))
            if flags & 4:
                ret.append(t.getViewHTML(field, node, flags, language=language))
            else:
                ret += t.getViewHTML(field, node, flags, language=language)
        return ret

    def getMaskFields(self):
        ret = []
        for field in self.getAllChildren():
            if field.getType().getName()=="maskitem":
                ret.append(field)
        return ret


    """ return all fields which are empty """
    def validate(self, nodes):
        ret = []
        for node in nodes:
            for item in self.getMaskFields():
                field = item.getField()
                if item.getRequired()==1:
                    if node.get(field.getName())=="":
                        ret.append(field.id)

                if field and field.getType().getName()=="metafield" and field.getFieldtype()=="date":
                    if not node.get(field.getName())=="" and not validateDateString(node.get(field.getName())):
                        ret.append(field.id)
        return ret

    """ return all node ids which are empty """
    def validateNodelist(self, nodes):
        ret = []
        for node in nodes:
            for item in self.getMaskFields():
                field = item.getField()
                if item.getRequired()==1:
                    if node.get(field.getName())=="":
                        ret.append(node.id)

                if field and field.getType().getName()=="metafield" and field.getFieldtype()=="date":
                    #if not validateDateString(node.get(field.getName())):
                    if not node.get(field.getName())=="" and not validateDateString(node.get(field.getName())):
                        ret.append(node.id)
        return ret


    ''' update given node with given reques values '''
    def updateNode(self, nodes, req):
        for node in nodes:
            for item in self.getMaskFields():
                field = item.getField()
                if field and field.getType().getName()=="metafield" and req.params.get(field.getName(),"")!="? ":
                    t = getMetadataType(field.get("type"))
                    if field.getName() in req.params.keys():
                        value = t.getFormatedValueForDB(field, req.params.get(field.getName()))
                        node.set(field.getName(), value)
                    elif field.getFieldtype() == "check":
                        node.set(field.getName(), 0)
        return nodes

    ''' show maskeditor - definition '''
    def getMetaMask(self, language=None):
        ret = '<form method="post" name="myform">'
        ret += '<div class="back"><h3 i18n:translate="mask_editor_field_definition">Felddefinition </h3><div align="right"><input type="image" src="/img/install.png" name="newdetail_'+self.id+'" i18n:attributes="title mask_editor_new_line_title"/></div><br/>'
        if len(self.getChildren())==0:
            ret += '<div i18n:translate="mask_editor_no_fields">- keine Felder definiert -</div>'
        
        i=0
        fieldlist = getAllMetaFields()
        for item in self.getChildren().sort():
            t = getMetadataType(item.get("type"))
            ret += t.getMetaHTML(self, i, language=language, fieldlist=fieldlist) # get formated line specific of type (e.g. field)
            i += 1
        ret += '</form>'
        return ret

    """ """
    def editItem(self, req):
        for key in req.params.keys():
            # edit field
            if key.startswith("edit_"):
                item = tree.getNode(req.params.get("edit", ""))
                t = getMetadataType(item.get("type")) 
                ret = '<form method="post" name="myform">'
                ret += t.getMetaEditor(item, req)
                ret += '</form>'
                return ret

        if req.params.get("op","")=="new" and req.params.get("type","")!="":
            # add field
            item = Maskitem(name="", type="maskitem")
            t = getMetadataType(req.params.get("type"))
            if req.params.get("type","")=="hgroup":
                req.params["edit"] = item
            elif req.params.get("type","")=="vgroup":
                req.params["edit"] = item
            else:
                req.params["edit"] = item.id
            ret = '<form method="post" name="myform">'
            ret += t.getMetaEditor(item, req)
            ret += '</form>'
            return ret

        if req.params.get("type","")=="":
            # type selection for new field
            ret = """
            <form method="post" name="myform">
                <div class="back"><h3 i18n:translate="mask_editor_add_choose_fieldtype">Feldtyp w&auml;hlen</h3>
                <div class="label" i18n:translate="mask_editor_field_selection">Feldtypauswahl:</div>
                <select name="type">
                    <option value="field" i18n:translate="mask_editor_normal_field">Normales Feld</option>
                    <option value="vgroup" i18n:translate="mask_editor_vert_group">Vertikale Feldgruppe</option>
                    <option value="hgroup" i18n:translate="mask_editor_hor_group">Horizontale Feldgruppe</option>
                    <option value="label" i18n:translate="mask_editor_label">Label</option>
                </select>
                <br/>
                <br/>
                <span i18n:translate="mask_editor_msg1">F&uuml;r Maskenfelder stehen verschiedene Typen zur Verf&uuml;gung, die jeweils unterschiedliche Darstellungen erlauben. Standard ist das 'Normale Feld'</span>
                <br/>
                <br/>
                <input type="hidden" name="op" value="new"/>"""
            ret += '<input type="hidden" name="pid" value="'+str(req.params.get("pid"))+'"/>'
            ret += '<div class="label">&nbsp;</div><button type="submit" name="new_" style="width:100px" i18n:translate="mask_editor_ok"> OK </button>'
            ret += '&nbsp;&nbsp;<button type="submit" onclick="setCancel(document.myform.op)" i18n:translate="mask_editor_cancel">Abbrechen</button><br/>'
            ret += '</div></form>'
            return req.getTALstr(ret, {})

        if req.params.get("edit"," ")==" " and req.params.get("op","")!="new":
            # create new node
            item = tree.getNode(req.params.get("id"))
            t = getMetadataType(req.params.get("type"))
            ret = '<form method="post" name="myform">'
            ret += t.getMetaEditor(item, req)
            ret += '</form>'
            return ret

    def getDescription(self):
        return self.get("description")
    def setDescription(self, value):
        self.set("description", value)

    def getFieldtype(self):
        return self.get("type")

    def getMasktype(self):
        return self.get("masktype")
    def setMasktype(self, value):
        self.set("masktype", value)

    def addMaskitem(self, label, type, fieldid, pid):
        item = Maskitem(name=label, type="maskitem") 
        item.set("type", type)
        
        if fieldid!=0:
            for id in str(fieldid).split(";"):
                try:
                    field = tree.getNode(long(id))
                    # don't remove field- it may
                    # (a) be used for some other mask item or
                    # (b) still be in the global metadatafield list
                    #for p in field.getParents():
                    #    p.removeChild(field)
                    item.addChild(field)
                except ValueError:
                    print "node id error for id '", id,"'"
        if str(pid)=="0":
            self.addChild(item)
        else:
            node = tree.getNode(pid)
            node.addChild(item)
        return item

    ''' delete given  maskitem '''
    def deleteMaskitem(self, itemid):
        item = tree.getNode(itemid)
        for parent in item.getParents():
            parent.removeChild(item)
            i=0
            for child in parent.getChildren().sort():
                child.setOrderPos(i)
                i += 1

""" class for editor/view masks """
class Maskitem(tree.Node):

    def getLabel(self):
        return self.getName()
    def setLabel(self, value):
        self.setName(value)

    def getField(self):
        if self.getNumChildren():
            return self.getChildren()[0]
        else:
            return None

    def getDescription(self):
        if not self.get("description") and self.getField():
            return self.getField().getDescription() 
        else:
            return self.get("description")
    def setDescription (self,value):
        if not self.get("description") and self.getField():
            self.getField().setDescription(value)
        else:
            self.set("description",value)

    def getRequired(self):
        if self.get("required"):
            return int(self.get("required"))
        else:
            return 0
    def setRequired(self, value):
        self.set("required", str(value))

    def getWidth(self):
        if self.get("width"):
            return int(self.get("width"))
        else:
            return 400
    def setWidth(self, value=400):
        self.set("width", str(value))

    def getDefault(self):
        return self.get("default")
    def setDefault(self, value):
        self.set("default", str(value))

    def getUnit(self):
        return self.get("unit")
    def setUnit(self, value):
        self.set("unit", str(value))

""" fields for metadata """
class Metadatafield(tree.Node):
    def getName(self):
        return self.get("name")
    def setName(self, value):
        self.set("name", value)

    def getLabel(self):
        return self.get("label")
    def setLabel(self, value):
        self.set("label", value)

    def getFieldtype(self):
        return self.get("type")
    def setFieldtype(self, value):
        self.set("type", value)

    def getOption(self):
        return self.get("opts")
    def setOption(self, value):
        self.set("opts", value)

    def getFieldOptionList(self):
        global fieldoption
        retList = []
        for option in fieldoption:
            if option.value in self.getOption() and option.value!="":
                retList += [True]
            else:
                retList += [False]
        return retList

    def getDescription(self):
        return self.get("description")
    def setDescription(self, value):
        self.set("description", value)
    
    def getFieldValueNum(self):
        return self.get("valuelistnum")
    def setFieldValueNum(self, fnum):
        self.set("valuelistnum", fnum)

    def getValues(self):
        return self.get("valuelist").replace(";","\r\n")
    def setValues(self, value):
        self.set("valuelist", value)

    def Searchfield(self):
        return "s" in self.getOption()
    
    def getValueList(self):
        return self.getValues().split("\r\n")
    def setValuelist(self, valuelist):
        self.set("valuelist", "; ".join(["%s" %k for k in valuelist]))
    
    def getSystemFormat(self, shortname):
        for option in dateoption:
            if option.getShortName() == shortname:
                return option
        return dateoption[0]

    def getValue(self, node):
        if self.get("fieldtype") == "date":
            d = self.getSystemFormat(str(self.fieldvalues))
            v = node.get(self.name)
            try:
                value = date.format_date(date.parse_date(v), d.getValue())
            except ValueError:
                value = v
        else:
            value = node.get(self.name)
        return value

    def getEditorHTML(self, val="", width=400, name="", lock=0, language=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")
        return t.getEditorHTML(self, val, width, name, lock, language=language)

    def getSearchHTML(self, val="", width=174, name="", language=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")
        return t.getSearchHTML(self, val, width, name, language=language)

    def getFormatedValue(self, node, language=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")

        return t.getFormatedValue(self, node, language=language)

mytypes = {}

def pluginClass(newclass):
    global mytypes
    name = newclass.__name__
    if name.startswith("m_"):
        name = name[2:]
    mytypes[name] = newclass

def pluginModule(module):
    class Dummyclass:
        pass
    for name,obj in module.__dict__.items():
        if name.startswith("m_") and type(obj) == type(Dummyclass):
            pluginClass(obj)

def init():
    global mytypes
    ret = {}
    for root, dirs, files in os.walk(os.path.join(config.basedir, 'metatypes')):
        for name in files:
            if name.startswith("m_") and name.endswith(".py"):
                name = name[:-3]
                if root.endswith('metatypes'):
                    pluginModule(__import__("metatypes."+name).__dict__[name])
                if root.endswith('mask'):
                    pluginModule(__import__("metatypes.mask."+name).__dict__["mask"].__dict__[name])


def getMetadataType(mtype):
    global mytypes
    init()
    if mtype in mytypes:
        return mytypes[mtype]()
    else:
        raise LookupError("No such metatype: "+mtype)

def getMetaFieldTypeNames():
    ret = {}
    global mytypes
    init()
    for key in mytypes.keys():
        ret[key] = "fieldtype_"+key
    return ret

def getMetaFieldTypes():
    global mytypes
    ret = {}
    for t in mytypes:
        ret[t] = getMetadataType(t)
    return ret

init()
