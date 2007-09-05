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
import date
import logging
import search.query
import xml
import traceback
import tree

from utils import *
from tree import nodeclasses
from config import *
from xmlnode import getNodeXML, readNodeXML

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
dateoption +=[Option("metafield_dateformat_year", "yyyy", "%Y" )]
dateoption +=[Option("metafield_dateformat_yearmonth", "yyyy-mm", "%Y-%m" )]
dateoption +=[Option("metafield_dateformat_month", "mm", "%m" )]
dateoption +=[Option("metafield_dateformat_time", "hh:mm:ss", "%H:%M:%S" )]

VIEW_DEFAULT = 0        # default view for masks
VIEW_SUB_ELEMENT = 1    # internal parameter
VIEW_HIDE_EMPTY = 2     # show only fields with 'non-empty' values
VIEW_DATA_ONLY = 4      # deliver list with values (not html)

#
# return metadata object by given name
#
def getMetaType(name):
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
    return list(tree.getRoot("metadatatypes").getChildren().sort())

def getNumberNodes(name):
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
def updateMetaType(name, description="", longname="", active=0, datatypes="", orig_name=""):
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
# returns all fields for given metatype
#
def getFieldsForMeta(name):
    return list(getMetaType(name).getMetaFields())

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
def updateMetaField(parent, name, label, orderpos, fieldtype, option="", description="", fieldvalues="", fieldvaluenum="", orig_name=""):
    metatype = getMetaType(parent)
    try:
        field = metatype.getChild(orig_name)
        field.setName(name)
        #field.setOrderPos(orderpos)
    except tree.NoSuchNodeError:
        field = tree.Node(name=name, type="metafield")
        metatype.addChild(field)
        field.setOrderPos(len(metatype.getChildren())-1)
        
    field.set("label", label)
    
    field.set("type", fieldtype)
    field.set("opts", option)
    field.set("valuelist", fieldvalues.replace("\r\n",";"))
    field.set("valuelistnum", fieldvaluenum)
    field.set("description", description)



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
    up, down = -1,-1
   
    if direction==1:
        down = int(getMetaField(pid, name).getOrderPos())
    elif direction==-1:
        up = int(getMetaField(pid, name).getOrderPos())

    i = 0
    for field in getMetaType(pid).getChildren().sort():
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

            if pos<0:
                pos=0
            field.setOrderPos(pos)
            i = i + 1
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
        i=0
        for c in metatype.getChildren().sort():
            if c.type!="mask": 
                if c.getFieldtype()!="union":
                    n = tree.Node(c.get("label"), "maskitem")
                    n.setOrderPos(i)
                    i+=1
                    field = mask.addChild(n)
                    field.set("width", "400")
                    field.set("type", "field")
                    field.addChild(c)

def cloneMask(mask, newmaskname):
    def recurse(m1,m2):
        for k,v in m1.items():
            m2.set(k,v)
        for c1 in m1.getChildren().sort():
            if c1.type == "mask" or c1.type == "maskitem":
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
        if f.type != "mask":
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
        
        if currentparent.type != "maskitem":
            if verbose:
                print "Field",node.id,node.name,"is not below a maskitem (parent:",currentparent.id,currentparent.name,")"
            error = error + 1 
            if fix:
                currentparent.removeChild(node)
            return

        for parent in node.getParents():
            if parent.type == "metadatatype":
                return #OK
            elif parent.type == "maskitem":
                pass 
            elif parent.type == "mask":
                pass
            else:
                print "Node",node.id,node.name,"has strange parent",parent.id,parent.name

        error = error + 1

        if node.name in field2node:
            node2 = field2node[node.name]
            if verbose:
                print "Node",node.id,node.name,"has/had no entry in metadatatypes (but field with name",node.name,"exists there:",node2.id
            c = 0
            if node.get("required") != node2.get("required"):
                if verbose:
                    print "required",node.get("required"),"<->","required",node2.get("required")
                c = c + 1
            elif node.get("type") != node2.get("type"):
                if verbose:
                    print "type",node.get("type"),"<->","type",node2.get("type")
                c = c + 1
            elif node.get("label") != node2.get("label"):
                if verbose:
                    print "label",node.get("label"),"<->","label",node2.get("label")
                c = c + 1
            elif node.get("opts") != node2.get("opts"):
                if verbose:
                    print "opts",node.get("opts"),"<->","opts",node2.get("opts")
                c = c + 1
            if c == 0 and fix:
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
        if allowedFields and name not in allowedFields:
            continue
        value = node.get(name)
        lock = 0

        #_helpLink = "&nbsp;"
        #if field.description != "":
        #    _helpLink = """<a href="#" onclick="openPopup(\'/popup_help?pid=""" + field.pid + """&name=""" + field.name + """\', \'\', 400, 250)"><img src="img/tooltip.png" border="0"></a>"""
        if (field.getRequired()>0):
            result += ('<tr><td align="left">'+field.getLabel()+': <span class="required">*</span></td>')
        else:
            result += ('<tr><td align="left">'+field.getLabel()+':</td>')

        result += ('<td align="left">')
        result += (field.getEditorHTML(value,400,name,lock))
        result += ('</td></tr>')
        
    result += ('<tr><td>&nbsp;</td><td align="left"><small>(<span class="required">*</span> Pflichtfeld, darf nicht leer sein)</small></td></tr>')
    result += ('<input type="hidden" name="metaDataEditor" value="metaDataEditor">')
    
    for k,v in hiddenvalues.items():
        result += ("""<input type="hidden" name="%s" value="%s">\n""" % (k,v))
    return result


def parseEditorData(req,node):
    fields = node.getType().getMetaFields()

    nodes = [node]

    incorrect = False
    for field in fields:
        name = field.getName()
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

            if field.getType() == "date":
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
    if n.getType().getName()=="metadatatype":
        importlist.append(n)
    elif n.getType().getName()=="metadatatypes":
        for ch in n.getChildren():
            importlist.append(ch)

    metadatatypes = tree.getRoot("metadatatypes")
    for m in importlist:
        m.setName("import-"+m.getName())
        metadatatypes.addChild(m)
