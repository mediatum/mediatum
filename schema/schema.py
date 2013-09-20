"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Iryna Feuerstein <feuersti@in.tum.de>

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
import sys
import utils.date
import logging
import xml
import traceback
import core.tree as tree
import core.config as config
import core.translation as translation

from utils.utils import *
from utils.date import *
from utils.log import logException
from core.tree import nodeclasses, Node, FileNode
from core.config import *
from core.xmlnode import getNodeXML, readNodeXML
from core.db.database import getConnection
from core.metatype import Context


log = logging.getLogger('backend')

requiredoption = []
requiredoption += [Option("Kein Pflichtfeld", "notmandatory", "0", "/img/req2_opt.png")]
requiredoption += [Option("Pflichtfeld, darf nicht leer sein", "mandatory1", "1", "/img/req0_opt.png")]
requiredoption += [Option("Pflichtfeld, muss eine Zahl sein", "mandatory2", "2", "/img/req1_opt.png")]

fieldoption = []
fieldoption += [Option("metafield_option1", "search", "s", "/img/folder_plus.gif")]
fieldoption += [Option("metafield_option2", "sort", "o", "/img/ordersel.png")]

dateoption = []
dateoption +=[Option("metafield_dateformat_std", "dd.mm.yyyy", "%d.%m.%Y" )]
dateoption +=[Option("metafield_dateformat_long", "dd.mm.yyyy hh:mm:ss", "%d.%m.%Y %H:%M:%S" )]
dateoption +=[Option("metafield_dateformat_year", "yyyy", "%Y" )]
dateoption +=[Option("metafield_dateformat_yearmonth", "yyyy-mm", "%Y-%m" )]
dateoption +=[Option("metafield_dateformat_month", "mm", "%m" )]
dateoption +=[Option("metafield_dateformat_time", "hh:mm:ss", "%H:%M:%S" )]

VIEW_DEFAULT = 0        # default view for masks
VIEW_SUB_ELEMENT = 1    # internal parameter
VIEW_HIDE_EMPTY = 2     # show only fields with 'non-empty' values
VIEW_DATA_ONLY = 4      # deliver list with values (not html)
VIEW_DATA_EXPORT = 8    # deliver export format

#
# return metadata object by given name
#
def getMetaType(name):

    if name.isdigit():
        return tree.getNode(name)

    if name.find("/")>0:
        name = name[name.rfind("/")+1:]

    metadatatypes = tree.getRoot("metadatatypes")
    try:
        return metadatatypes.getChild(name)
    except tree.NoSuchNodeError,e:
        return None

#
# load all meta-types from db
#
def loadTypesFromDB():
    return list(tree.getRoot("metadatatypes").getChildren().sort('name'))

def getNumberNodes(name):
    return 1
    return len(tree.getRoot("metadatatypes").search("objtype=%s*" % (name)))

#
# check if metatype with given name is still existing in db
#
def existMetaType(name):
    if getMetaType(name):
        return True
    return False


#
# update/create metatype by given object
#
def updateMetaType(name, description="", longname="", active=0, datatypes="", bibtexmapping="", orig_name=""):
    metadatatypes = tree.getRoot("metadatatypes")
    try:
        metadatatype = metadatatypes.getChild(orig_name)
        metadatatype.setName(name)
    except tree.NoSuchNodeError:
        metadatatype = tree.Node(name=name, type="metadatatype")
        metadatatypes.addChild(metadatatype)

    metadatatype.set("description", description)
    metadatatype.set("longname", longname)
    metadatatype.set("active", str(active))
    metadatatype.set("datatypes", datatypes)
    metadatatype.set("bibtexmapping", bibtexmapping)


#
# delete metatype by given name
#
def deleteMetaType(name):
    metadatatypes = tree.getRoot("metadatatypes")
    metadatatypes.removeChild(getMetaType(name))

###################################################
#                detail section                   #
###################################################

#
# returns a fieldlist with name as key and list of metatypes as value
#
def getAllMetaFields():
    fields = {}
    for mtype in loadTypesFromDB():
        for field in getFieldsForMeta(mtype.getName()):
            if field.getName() not in fields.keys():
                fields[field.getName()] = [mtype]
            else:
                if mtype not in fields[field.getName()]:
                    fields[field.getName()].append(mtype)
    return fields


#
# returns field for given name and metatype
#
def getMetaField(pid, name):
    try:
        return getMetaType(pid).getChild(name)
    except tree.NoSuchNodeError,e:
        return None


#
# check existance of field for given metadatatype
#
def existMetaField(pid, name):
    try:
        f = getMetaType(pid).getChild(name)
        return True
    except:
        return False


""" update/create metadatafield """
def updateMetaField(parent, name, label, orderpos, fieldtype, option="", description="", fieldvalues="", fieldvaluenum="", fieldid="", filenode=None, attr_dict={}):
    metatype = getMetaType(parent)
    try:
        field = tree.getNode(fieldid)
        field.setName(name)
    except tree.NoSuchNodeError:
        field = tree.Node(name=name, type="metafield")
        metatype.addChild(field)
        field.setOrderPos(len(metatype.getChildren())-1)

    #<----- Begin: For fields of list type ----->

    if filenode:
        # all files of the field will be removed before a new file kann be added
        for fnode in field.getFiles():
            field.removeFile(fnode)         # remove the file from the node tree
            try:
                os.remove(fnode.retrieveFile()) # delete the file from the hard drive
            except Exception, e:
                logException(e)
        field.addFile(filenode)

    if fieldvalues.startswith("multiple"):
        field.set("multiple", True)
        fieldvalues = fieldvalues.replace("multiple;", "", 1)
    else:
        field.removeAttribute("multiple")

    if fieldvalues.endswith("delete"): # the checkbox 'delete' was checked
        # all files of the field will be removed
        for fnode in field.getFiles():
            field.removeFile(fnode)         # remove the file from the node tree
            try:
                os.remove(fnode.retrieveFile()) # delete the file from the hard drive
            except Exception, e:
                logException(e)
        fieldvalues = fieldvalues.replace(";delete", "", 1)

    #<----- End: For fields of list type ----->

    field.set("label", label)
    field.set("type", fieldtype)
    field.set("opts", option)
    field.set("valuelist", fieldvalues.replace("\r\n",";"))
    field.set("valuelistnum", fieldvaluenum)
    field.set("description", description)

    for attr_name, attr_value in attr_dict.items():
        field.set(attr_name, attr_value)


#
# delete metadatafield
#
def deleteMetaField(pid, name):
    metadatatype = getMetaType(pid)
    field = getMetaField(pid, name)
    metadatatype.removeChild(field)

    i=0
    for field in getMetaType(pid).getChildren().sort():
        field.setOrderPos(i)
        i += 1

#
# change order of metadatafields: move element up/down
#
def moveMetaField(pid, name, direction):
    up, down = -1, -1

    if direction==1:
        down = int(getMetaField(pid, name).getOrderPos())
    elif direction==-1:
        up = int(getMetaField(pid, name).getOrderPos())

    i = 0
    for field in getMetaType(pid).getChildren().sort():
        try:
            if i==up:
                pos = i - 1
            elif i==up-1:
                pos = up
            elif i==down:
                pos = i + 1
            elif i==down+1:
                pos = down
            else:
                pos = i

            if pos<0:
                pos = 0
            field.setOrderPos(pos)
            i += 1
        except: # FIXME: what kind of exception is raised here?
            pass


def generateMask(metatype, masktype="", force=0):
    if force:
        try:
            metatype.removeChild(metatype.getChild(masktype))
        except: # if we can't remove the existing mask, it wasn't there, which is ok
            pass
    try:
        mask = metatype.getChild(masktype)
        return # mask is already there- nothing to do!
    except tree.NoSuchNodeError:
        mask = metatype.addChild(tree.Node("-auto-","mask"))
        i = 0
        for c in metatype.getChildren().sort():
            if c.type!="mask":
                if c.getFieldtype()!="union":
                    n = tree.Node(c.get("label"), "maskitem")
                    n.setOrderPos(i)
                    i += 1
                    field = mask.addChild(n)
                    field.set("width", "400")
                    field.set("type", "field")
                    field.addChild(c)

def cloneMask(mask, newmaskname):
    def recurse(m1,m2):
        for k,v in m1.items():
            m2.set(k,v)
        for c1 in m1.getChildren().sort():
            if c1.type in ["mask", "maskitem"]:
                c2 = tree.Node(c1.getName(), c1.type)
                c2.setOrderPos(c1.getOrderPos())
                m2.addChild(c2)
                recurse(c1,c2)
            else:
                m2.addChild(c1)

    p = mask.getParents()
    if len(p)==0:
        raise "Mask has no parents"
    if len(p)>1:
        raise "Mask has more than one parent"
    if mask.type != "mask":
        raise "Not a mask"
    newmask = tree.Node(newmaskname, mask.type)
    p[0].addChild(newmask)
    recurse(mask, newmask)


def checkMask(mask,fix=0,verbose=1,show_unused=0):
    if mask.type != "mask":
        if verbose:
            print "Node",mask.id,mask.name,"is no mask"
        return 1
    p = mask.getParents()
    if len(p)>1:
        if verbose:
            print "Mask has more than one parent"
        return 1
    if len(p)==0:
        if verbose:
            print "Mask has no parents (?)"
        return 1

    metatypes = p[0]
    field2node = {}
    fieldsused = {}
    masks = []
    for f in metatypes.getChildren():
        if f.type!="mask":
            field2node[f.name] = f
            fieldsused[f.name] = 0
        else:
            masks += [f]

    global error
    error = 0
    def recurse(node,currentparent):
        global error
        if node.type in ["mask","maskitem"]:
            for field in node.getChildren():
                recurse(field,node)
            return
        fieldsused[node.name] = 1

        if fix and node.get("orderpos"):
            if verbose:
                print "Removing orderpos attribute from node",node.id
            node.set("orderpos", "")

        if currentparent.type!="maskitem":
            if verbose:
                print "Field",node.id,node.name,"is not below a maskitem (parent:",currentparent.id,currentparent.name,")"
            error += 1
            if fix:
                currentparent.removeChild(node)
            return

        for parent in node.getParents():
            if parent.type=="metadatatype":
                return #OK
            elif parent.type in ["maskitem", "mask"]:
                pass
            else:
                print "Node",node.id,node.name,"has strange parent",parent.id,parent.name

        error += 1

        if node.name in field2node:
            node2 = field2node[node.name]
            if verbose:
                print "Node",node.id,node.name,"has/had no entry in metadatatypes (but field with name",node.name,"exists there:",node2.id
            c = 0
            if node.get("required") != node2.get("required"):
                if verbose:
                    print "required",node.get("required"),"<->","required",node2.get("required")
                c += 1
            elif node.get("type") != node2.get("type"):
                if verbose:
                    print "type",node.get("type"),"<->","type",node2.get("type")
                c += 1
            elif node.get("label") != node2.get("label"):
                if verbose:
                    print "label",node.get("label"),"<->","label",node2.get("label")
                c += 1
            elif node.get("opts") != node2.get("opts"):
                if verbose:
                    print "opts",node.get("opts"),"<->","opts",node2.get("opts")
                c += 1
            if c==0 and fix:
                currentparent.removeChild(node)
                currentparent.addChild(node2)
        else:
            if verbose:
                print "Node",node.id,node.name,"has/had no entry in metadatatypes"
            if fix:
                metatypes.addChild(node)

    recurse(mask,None)
    if show_unused:
        # go through the other masks, too
        for mask2 in masks:
            if mask!=mask2:
                recurse(mask2,None)
        # dump all presumably unused fields
        for name,used in fieldsused.items():
            if not used:
                field = metatypes.getChild(name)
                if "s" not in field.get("opts"):
                    print "Unused field:",field.id,field.name
    return error

def showEditor(node,hiddenvalues={}, allowedFields=None):
    result = ""
    fields = node.getType().getMetaFields()

    for field in fields:
        name = field.getName()
        langNames = None
        if field.get("text"):
            langNames = [lang + name for lang in config.get("i18n.languages").split(",")]
        if allowedFields and name not in allowedFields:
            continue
        value = ""
        if langNames:
            for langName in langNames:
                value += langName + "\n" + node.get(langName + "__" + name) + "\n"
        else:
            value = node.get(name)
        lock = 0

        #_helpLink = "&nbsp;"
        #if field.description != "":
        #    _helpLink = """<a href="#" onclick="openPopup(\'/popup_help?pid=""" + field.pid + """&name=""" + field.name + """\', \'\', 400, 250)"><img src="img/tooltip.png" border="0"></a>"""
        if (field.getRequired()>0):
            result += ('<tr><td align="left">'+field.getLabel()+': <span class="required">*</span></td>')
        else:
            result += '<tr><td align="left">%s:</td>' %(field.getLabel())
        result += '<td align="left">%s</td></tr>' %(field.getEditorHTML(value,400,lock))
    result += ('<tr><td>&nbsp;</td><td align="left"><small>(<span class="required">*</span> Pflichtfeld, darf nicht leer sein)</small></td></tr>')
    result += ('<input type="hidden" name="metaDataEditor" value="metaDataEditor">')

    for k,v in hiddenvalues.items():
        result += ("""<input type="hidden" name="%s" value="%s">\n""" % (k,v))
    return result


def parseEditorData(req,node):
    nodes = [node]
    incorrect = False
    defaultlang = translation.lang(req)

    for field in node.getType().getMetaFields():
        name = field.getName()
        if "%s__%s" %(defaultlang, name) in req.params:
            value = req.params.get("%s__%s" %(defaultlang, name), "? ")
        else:
            value = req.params.get(name, "? ")

        if value!="? ":
            #if (field.getRequired()==1):
            #    # not empty
            #    if (value==""):
            #        # error
            #        incorrect = True

            for node in nodes:
                node.set(name, value)

            #elif (field.getRequired()==2):
            #    # has to be a number
            #    try:
            #        x = float(value)
            #    except:
            #        # error
            #        incorrect = True

            #    for node in nodes:
            #        node.set(name, value)

            if field.getType()=="date":
                f = field.getSystemFormat(field.fieldvalues)
                try:
                    date = parse_date(str(value),f.getValue())
                except ValueError:
                    date = None
                if date:
                    value = format_date(date, format='%Y-%m-%dT%H:%M:%S')
                    for node in nodes:
                        node.set(name, value)
            else:
                for node in nodes:
                    node.set(name, value)
        else: # value not in request -> remove attribute
            node.removeAttribute(field.getName())
    return not incorrect


#
# export metadatascheme
#
def exportMetaScheme(name):
    if name=="all":
        return getNodeXML(tree.getRoot("metadatatypes"))
    else:
        return getNodeXML(getMetaType(name))


#
# import metadatatype from file
#
def importMetaSchema(filename):
    n = readNodeXML(filename)
    importlist = list()
    if n.getContentType()=="metadatatype":
        importlist.append(n)
    elif n.getContentType()=="metadatatypes":
        for ch in n.getChildren():
            importlist.append(ch)

    metadatatypes = tree.getRoot("metadatatypes")
    for m in importlist:
        m.setName("import-"+m.getName())
        metadatatypes.addChild(m)


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
            if item.getContentType()=="metafield":
                if not type or type in item.getOption():
                    fields.append(item)
        return fields

    def getMetaField(self, name):
        try:
            return self.getChild(name)
        except tree.NoSuchNodeError:
            # *shrug*
            return None

    def getMasks(self, type="", language=""):
        masks = []
        for item in self.getChildren().sort():
            if item.getContentType()=="mask":
                if type=="":
                    if item.getLanguage() in [language,"no"] or language=="":
                        masks.append(item)
                elif type==item.getMasktype():
                    if item.getLanguage() in [language,"no"] or language=="":
                        masks.append(item)
        return masks

    def getMask(self, name):
        try:
            if name.isdigit():
                return tree.getNode(name)
            else:
                return self.getChild(name)
        except tree.NoSuchNodeError:
            return None

    def searchIndexCorrupt(self):
        try:
            from core.tree import searcher
            search_def=[]
            for node in node_getSearchFields(self):
                search_def.append(node.getName())
            search_def = set(search_def)

            index_def = searcher.getDefForSchema(self.name)
            index_def = set(index_def.values())
            if len(search_def)>len(index_def) and len(self.getAllItems())>0:
                return True
            else:
                if search_def.union(index_def)==set([]) or index_def.difference(search_def)==set([]):
                    return False
            return True
        except:
            logException("error in searchIndexCorrupt")
            return False


    def getAllItems(self):
        ret = []
        l = getConnection().getNodeIDsForSchema(self.getName())
        for i in l:
            ret.append(i[0])
        return tree.NodeList(ret)


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

    def getSchemaNode(node):
        for p in node.getParents():
            if p.type=="metadatatype":
                return p
        return None

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
    def removeValue(self, value):
        self.set("valuelist", self.get("valuelist").replace(value,""))

    def Sortfield(self):
        return "o" in self.getOption()
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

    def getEditorHTML(self, val="", width=400, lock=0, language=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")
        return t.getEditorHTML(self, val, width, lock, language=language)

    def getSearchHTML(self, context):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")
        context.field = self
        return t.getSearchHTML(context)

    def getFormatedValue(self, node, language=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")

        return t.getFormatedValue(self, node, language=language)

# helper class for masks
class MaskType:
    def __init__(self, type, separator="<br/>"):
        self.type = type
        self.separator = separator

    def setType(self, value):
        self.type = value
    def getType(self):
        return self.type

    def setSeparator(self, value):
        self.separator = value
    def getSeparator(self):
        return self.separator

def getMaskTypes(key="."):
    masktypes = {
                    "":MaskType("masktype_empty"),
                    "edit":MaskType("masktype_edit"),
                    "search":MaskType("masktype_search"),
                    "shortview":MaskType("masktype_short",". "),
                    "fullview":MaskType("masktype_full"),
                    "export":MaskType("masktype_export")
                }
    if key==".":
        return masktypes
    else:
        if key in masktypes.keys():
            return masktypes[key]
        else:
            return MaskType()

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


    def getViewHTML(self, nodes, flags=0, language=None, template_from_caller=None, mask=None):
        if not self.getChildren():
            return []
        if flags & 4:
            ret = []
        else:
            ret = ""

        if flags & 8: # export mode
            x = self.getChildren()
            x.sort()
            return getMetadataType("mappingfield").getViewHTML(x, nodes, flags, language=language, template_from_caller=template_from_caller, mask=mask)

        for field in self.getChildren().sort():
            t = getMetadataType(field.get("type"))
            if flags & 4: # data mode
                v = t.getViewHTML(field, nodes, flags, language=language, template_from_caller=template_from_caller, mask=mask)
                format = field.getFormat()
                if format!="":
                    v[1] = format.replace("<value>", v[1])
                v.append(field.getSeparator())

                if flags & 2:   # hide empty
                    if v[1].strip()!="":
                        ret.append(v)
                else:
                    ret.append(v)
            else:
                ret += t.getViewHTML(field, nodes, flags, language=language, template_from_caller=template_from_caller, mask=mask)
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
            if field.getContentType()=="maskitem":
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

                if field and field.getContentType()=="metafield" and field.getFieldtype()=="date":
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

                if field and field.getContentType()=="metafield" and field.getFieldtype()=="date":
                    #if not validateDateString(node.get(field.getName())):
                    if not node.get(field.getName())=="" and not validateDateString(node.get(field.getName())):
                        ret.append(node.id)
        return ret

    ''' returns True if all mandatory fields of mappingdefinition are used -> valid format'''
    def validateMappingDef(self):
        mandfields = []
        if self.getMasktype()=="export":
            for mapping in self.get("exportmapping").split(";"):
                for c in tree.getNode(mapping).getMandatoryFields():
                    mandfields.append(c.id)
        for item in self.getMaskFields():
            try:
                mandfields.remove(item.get("mappingfield"))
            except ValueError: # id not in list
                pass
        return len(mandfields)==0



    ''' update given node with given request values '''
    def updateNode(self, nodes, req):
        default_language = translation.getDefaultLanguage()
        for node in nodes:
            for item in self.getMaskFields():
                field = item.getField()
                if field and field.getContentType()=="metafield" and req.params.get(field.getName(),"").find("?")!=0:
                    t = getMetadataType(field.get("type"))
                    if field.getName() in req.params.keys():
                        value = t.getFormatedValueForDB(field, req.params.get(field.getName()))
                        language = translation.lang(req)
                        node.set(field.getName(), value)
                    elif field.getFieldtype()=="check":
                        node.set(field.getName(), 0)

                    else:
                        # if multilingual textfields were used, their names are
                        # saved in form en__Name, de__Name, de-AU__Name, en-US__Name etc.
                        for item in req.params.keys():
                            langPos = item.find('__')
                            if langPos != -1 and item[langPos+2:] == field.getName():
                                # cut the language identifier (en__, fr__, etc)
                                if (req.params.get(str(field.id) + '_show_multilang','') == 'multi'
                                    and hasattr(t, "language_update")):
                                    value_old = node.get(field.getName())
                                    value_new = req.params.get(item)
                                    value = t.language_update(value_old, value_new, item[:langPos])
                                    node.set(field.getName(), value)
                                elif req.params.get(str(field.id) + '_show_multilang', '') == 'single':
                                    if item[0:langPos] == translation.lang(req):
                                        new_value = req.params.get(item)
                                        node.set(field.getName(), new_value)
                                elif (req.params.get(str(field.id) + '_show_multilang','') == 'multi'
                                     and not hasattr(t, "language_update")):
                                    value = t.getFormatedValueForDB(field, req.params.get(item))
                                    oldValue = node.get(field.getName())
                                    position = oldValue.find(item[:langPos]+t.joiner)
                                    if position != -1:
                                        # there is already a value for this language
                                        newValue = (oldValue[:position+langPos+len(t.joiner)]
                                                       + value
                                                       + oldValue[oldValue.find(t.joiner,
                                                                  position+langPos+len(t.joiner)):])
                                        node.set(field.getName(), newValue)
                                    else: # there is no value for this language yet
                                        if oldValue.find(t.joiner) == -1:
                                            # there are no values at all yet
                                            node.set(field.getName(), item[:langPos]+t.joiner+value+t.joiner)
                                        else:
                                            # there are some values for other languages, but not for the current
                                            node.set(field.getName(), oldValue+item[:langPos]+t.joiner+value+t.joiner)

                    ''' raise event for metafield-type '''
                    if hasattr(t,"event_metafield_changed"):
                        t.event_metafield_changed(node, field)
            ''' raise event for node '''
            if hasattr(node,"event_metadata_changed"):
                node.event_metadata_changed()
            if node.get('updatetime')<str(now()):
                node.set("updatetime", str(format_date()))

        return nodes

    def getMappingHeader(self):
        if self.getMasktype()=="export":
            if len(self.get("exportheader"))>0:
                return self.get("exportheader")
            elif len(self.get("exportmapping").split(";"))>1:
                return self.getExportHeader()
            else:
                c = tree.getNode(self.get("exportmapping"))
                return c.getHeader()
        return ""

    def getMappingFooter(self):
        if self.getMasktype()=="export":
            if len(self.get("exportfooter"))>0:
                return self.get("exportfooter")
            elif len(self.get("exportmapping").split(";"))>1:
                return self.getExportFooter()
            else:
                c = tree.getNode(self.get("exportmapping"))
                return c.getFooter()
        return ""

    ''' show maskeditor - definition '''
    def getMetaMask(self, language=None):
        ret = '<form method="post" name="myform">'
        ret += '<div class="back"><h3 i18n:translate="mask_editor_field_definition">Felddefinition </h3>'

        if self.getMasktype() == "export" and self.get("exportmapping") == "":
            # no mapping defined, we just emit an error msg and skip the rest
            ret += '<p i18n:translate="mask_editor_no_export_mapping_defined" class="error">TEXT</p></div><br/>'
            return ret

        ret += '<div align="right"><input type="image" src="/img/install.png" name="newdetail_'
        ret += self.id
        ret += '" i18n:attributes="title mask_editor_new_line_title"/></div><br/>'

        if not self.validateMappingDef():
            ret += '<p i18n:translate="mask_editor_export_error" class="error">TEXT</p>'

        if len(self.getChildren())==0:
            ret += '<div i18n:translate="mask_editor_no_fields">- keine Felder definiert -</div>'
        else:
            if self.getMappingHeader()!="":
                ret += '<div class="label" i18n:translate="mask_edit_header">TEXT</div><div class="row">%s</div>' %(esc(self.getMappingHeader()))

        i=0
        fieldlist = {} #!!!getAllMetaFields()
        for item in self.getChildren().sort():
            t = getMetadataType(item.get("type"))
            ret += t.getMetaHTML(self, i, language=language, fieldlist=fieldlist) # get formated line specific of type (e.g. field)
            i += 1

        if len(self.getChildren())>0:
            if self.getMappingFooter()!="":
                ret += '<div class="label" i18n:translate="mask_edit_footer">TEXT</div><div class="row">%s</div>' %(esc(self.getMappingFooter()))
        ret += '</form>'
        return ret

    """ """
    def editItem(self, req):
        for key in req.params.keys():
            # edit field
            if key.startswith("edit_"):
                item = tree.getNode(req.params.get("edit", ""))
                t = getMetadataType(item.get("type"))
                return '<form method="post" name="myform">%s</form>' %(t.getMetaEditor(item, req))

        if (req.params.get("op","")=="new" and req.params.get("type","")!="") or (self.getMasktype()=="export" and req.params.get("op","") in ["newdetail", "new"]):
            # add field
            item = tree.Node(name="", type="maskitem")
            if self.getMasktype()=="export": # export mask has no selection of fieldtype -> only field
                t = getMetadataType("field")
                req.params["op"] = "new"
            else:
                t = getMetadataType(req.params.get("type"))

            if req.params.get("type","") in ["hgroup", "vgroup"]:
                req.params["edit"] = item
            else:
                req.params["edit"] = item.id
            return '<form method="post" name="myform">%s</form>' %(t.getMetaEditor(item, req))

        if (req.params.get("type","")=="" and self.getMasktype()!="export") or req.params.get('op')=='newdetail':
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
            return '<form method="post" name="myform">%s</form>' %(t.getMetaEditor(item, req))

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

    def getExportMapping(self):
        return self.get("exportmapping").split(";")
    def setExportMapping(self, exportmapping):
        self.set("exportmapping", exportmapping)

    def getExportHeader(self):
        return self.get("exportheader")
    def setExportHeader(self, header):
        self.set("exportheader", header)

    def getExportFooter(self):
        return self.get("exportfooter")
    def setExportFooter(self, footer):
        self.set("exportfooter", footer)

    def getExportOptions(self):
        return self.get("exportoptions")
    def setExportOptions(self, options):
        self.set("exportoptions", options)
    def hasExportOption(self, option):
        if option in self.get("exportoptions"):
            return True
        return False


    def getLanguage(self):
        if self.get("language")=="":
            return "no"
        return self.get("language")
    def setLanguage(self, value):
        self.set("language", value)

    def getDefaultMask(self):
        if self.get("defaultmask")=="True":
            return True
        return False
    def setDefaultMask(self, value):
        if value:
            self.set("defaultmask", "True")
        else:
            self.set("defaultmask", "False")

    def getSeparator(self):
        for key, value in self.items():
            if key=="separator":
                return self.get("separator")
        return getMaskTypes(self.getMasktype()).getSeparator()

    def setSeparator(self, value):
        self.set("separator", value)

    def addMaskitem(self, label, type, fieldid, pid):
        item = tree.Node(name=label, type="maskitem")
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
            i = 0
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

    def getTestNodes(self):
        return self.get("testnodes")
    def setTestNodes(self, value):
        self.set("testnodes", str(value))

    def getMultilang(self):
        field = [c for c in self.getChildren() if c.type=="metafield"]
        if len(field)>0:
            if field[0].get("multilang"):
                return 1
        return 0
    def setMultilang(self, value):
        field = [c for c in self.getChildren() if c.type=="metafield"]
        if len(field)>0:
            field[0].set("multilang", str(value))

    def getUnit(self):
        return self.get("unit")
    def setUnit(self, value):
        self.set("unit", str(value))

    def getFormat(self):
        return self.get("format")
    def setFormat(self, value):
        self.set("format", value)

    def getSeparator(self):
        return self.get("separator") or ""
    def setSeparator(self, value):
        self.set("separator", value)

mytypes = {}

def pluginClass(newclass):
    global mytypes
    name = newclass.__name__
    if name.startswith("m_"):
        name = name[2:]
    mytypes[name] = newclass
    if hasattr(newclass(), "getLabels"):
        translation.addLabels(newclass().getLabels())

def pluginModule(module):
    class Dummyclass:
        pass
    for name,obj in module.__dict__.items():
        if name.startswith("m_") and type(obj) == type(Dummyclass):
            pluginClass(obj)

def init(path):
    global mytypes
    ret = {}
    for root, dirs, files in path:
        for name in files:
            if name.endswith(".py") and name!="__init__.py":
                name = name[:-3]
                if root.endswith('metadata'):
                    pluginModule(__import__("metadata."+name).__dict__[name])
                if root.endswith('mask'):
                    pluginModule(__import__("schema.mask."+name).__dict__["mask"].__dict__[name])

def getMetadataType(mtype):
    global mytypes
    if len(mytypes)==0:
        init(os.walk(os.path.join(config.basedir, 'schema/mask')))
    if mtype in mytypes:
        return mytypes[mtype]()
    else:
        raise LookupError("No such metatype: "+mtype)

def getMetaFieldTypeNames():
    ret = {}
    global mytypes
    if len(mytypes)==0:
        init(os.walk(os.path.join(config.basedir, 'metadata')))
    for key in mytypes.keys():
        if "meta" in str(mytypes[key]):
            ret[key] = "fieldtype_"+key
    return ret

def getMetaFieldTypes():
    global mytypes
    ret = {}
    for t in mytypes:
        if getMetadataType(t).isFieldType():
            ret[t] = getMetadataType(t)
    return ret

""" return fields based on the schema name """
def getFieldsForMeta(name):
    return list(getMetaType(name).getMetaFields())

""" return fields based on node class and schema name """
def node_getMetaFields(node,type=None):
    try:
        l = node.metaFields()
    except:
        l = []

    try:
        if node.getSchema():
            l += getMetaType(node.getSchema()).getMetaFields(type)
    except AttributeError:
        pass
    return l

def node_getMetaField(node, name):
    if node.getSchema():
        try:
            metadatatype = getMetaType(node.getSchema())
            return getMetaType(node.getSchema()).getMetaField(name)
        except AttributeError:
            return None
    else:
        return None

def node_getSearchFields(node):
    sfields = []
    fields = node.getMetaFields()
    fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
    for field in fields:
        if field.Searchfield():
            sfields += [field]
    return sfields

def node_getSortFields(node):
    sfields = []
    fields = node.getMetaFields()
    fields.sort(lambda x, y: cmp(x.getOrderPos(),y.getOrderPos()))
    for field in fields:
        if field.Sortfield():
            sfields += [field]
    return sfields

def node_getMasks(node, type="", language=""):
    try:
        if node.getSchema():
            return getMetaType(node.getSchema()).getMasks(type=type, language=language)
        else:
            return []
    except AttributeError:
        return []


def node_getMask(node, name):
    if node.getSchema():
        try:
            return getMetaType(node.getSchema()).getMask(name)
        except AttributeError:
            return None
    else:
        raise ValueError("Node of type '"+str(node.getSchema())+"' has no mask")

def node_getDescription(node):
    if node.getSchema():
        mtype = getMetaType(node.getSchema())
        if mtype:
            return mtype.getDescription()
        else:
            return ""


init(os.walk(os.path.join(config.basedir, 'schema/mask')))
init(os.walk(os.path.join(config.basedir, 'metadata')))
