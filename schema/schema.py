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
import datetime
import inspect
import importlib
import logging
import os
import pkgutil
import sys
from warnings import warn

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import undefer
from werkzeug.utils import cached_property
import core.config as config
import core.translation as translation
from core import Node
from core.xmlnode import getNodeXML, readNodeXML
from core.metatype import Metatype
from core import db
from core.systemtypes import Metadatatypes
from core.transition.postgres import check_type_arg
from core.database.postgres.node import children_rel, parents_rel
from utils.date import parse_date, format_date, validateDateString
from utils.utils import Option, esc


log = logg = logging.getLogger(__name__)
q = db.query


requiredoption = []
requiredoption += [Option("Kein Pflichtfeld", "notmandatory", "0", "/img/req2_opt.png")]
requiredoption += [Option("Pflichtfeld, darf nicht leer sein", "mandatory1", "1", "/img/req0_opt.png")]
requiredoption += [Option("Pflichtfeld, muss eine Zahl sein", "mandatory2", "2", "/img/req1_opt.png")]

fieldoption = []
fieldoption += [Option("metafield_option1", "search", "s", "/img/folder_plus.gif")]
fieldoption += [Option("metafield_option2", "sort", "o", "/img/ordersel.png")]

dateoption = []
dateoption += [Option("metafield_dateformat_std",
                      "dd.mm.yyyy",
                      "%d.%m.%Y",
                      validation_regex='^(0[0-9]|1[0-9]|2[0-9]|3[01])\.(0[0-9]|1[012])\.[0-9]{4}$')]
dateoption += [Option("metafield_dateformat_long",
                      "dd.mm.yyyy hh:mm:ss",
                      "%d.%m.%Y %H:%M:%S",
                      validation_regex='^(0[0-9]|1[0-9]|2[0-9]|3[01])\.(0[0-9]|1[012])\.[0-9]{4} (0[0-9]|1[0-9]|2[0-3])(:[0-5][0-9]){2}$')]
dateoption += [Option("metafield_dateformat_year",
                      "yyyy",
                      "%Y",
                      validation_regex='^[0-9]{4}$')]
dateoption += [Option("metafield_dateformat_yearmonth",
                      "yyyy-mm",
                      "%Y-%m",
                      validation_regex='^[0-9]{4}-(0[0-9]|1[012])$')]
dateoption += [Option("metafield_dateformat_month",
                      "mm",
                      "%m",
                      validation_regex='^(0[0-9]|1[012])$')]
dateoption += [Option("metafield_dateformat_time",
                      "hh:mm:ss",
                      "%H:%M:%S",
                      validation_regex='^(0[0-9]|1[0-9]|2[0-3])(:[0-5][0-9]){2}$')]

VIEW_DEFAULT = 0        # default view for masks
VIEW_SUB_ELEMENT = 1    # internal parameter
VIEW_HIDE_EMPTY = 2     # show only fields with 'non-empty' values
VIEW_DATA_ONLY = 4      # deliver list with values (not html)
VIEW_DATA_EXPORT = 8    # deliver export format

#
# return metadata object by given name
#


def getMetaType(name):
    warn("use q(Metadatatype) instead", DeprecationWarning)
    if name.isdigit():
        nid = int(name)
        return q(Metadatatype).get(nid)

    if name.find("/") > 0:
        name = name[name.rfind("/") + 1:]

    return q(Metadatatype).filter_by(name=name).scalar()

#
# load all meta-types from db
#

def loadTypesFromDB():
    warn("use q(Metadatatype) instead", DeprecationWarning)
    return list(q(Metadatatype).order_by("name"))


def get_permitted_schemas():
    return q(Metadatatype).filter(Metadatatype.a.active == "1").filter_read_access().order_by(Metadatatype.a.longname).all()


def get_permitted_schemas_for_datatype(datatype):
    return [sc for sc in get_permitted_schemas() if datatype in sc.getDatatypes()]


#
# check if metatype with given name is still existing in db
#


def existMetaType(name):
    warn("use q(Metadatatype) instead", DeprecationWarning)
    if getMetaType(name):
        return True
    return False


#
# update/create metatype by given object
#
def updateMetaType(name, description="", longname="", active=0, datatypes="", bibtexmapping="", orig_name="", citeprocmapping=""):
    metadatatypes = q(Metadatatypes).one()
    metadatatype = metadatatypes.children.filter_by(name=orig_name).scalar()

    if metadatatype is not None:
        metadatatype.name = name
    else:
        metadatatype = Metadatatype(name)
        metadatatypes.children.append(metadatatype)

    metadatatype.set("description", description)
    metadatatype.set("longname", longname)
    metadatatype.set("active", ustr(active))
    metadatatype.set("datatypes", datatypes)
    metadatatype.set("bibtexmapping", bibtexmapping)
    metadatatype.set("citeprocmapping", citeprocmapping)
    db.session.commit()

#
# delete metatype by given name
#


def deleteMetaType(name):
    metadatatypes = q(Metadatatypes).one()
    metadatatype = q(Metadatatype).filter_by(name=name).one()
    metadatatypes.children.remove(metadatatype)
    db.session.commit()


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
    metatype = getMetaType(pid)
    if metatype is None:
        return None
    return metatype.children.filter_by(name=name).scalar()

#
# check existance of field for given metadatatype
#
def existMetaField(pid, name):
    return getMetaField(pid, name) is not None

""" update/create metadatafield """


def updateMetaField(parent, name, label, orderpos, fieldtype, option="", description="",
                    fieldvalues="", fieldvaluenum="", fieldid="", filenode=None, attr_dict={}):
    metatype = getMetaType(parent)
    field = None

    if fieldid:
        field = q(Node).get(fieldid)

    if field is not None:
        field.name = name
    elif name in [c.name for c in metatype.children]:
        for c in metatype.children:
            if c.name == name:
                field = c
                break
    else:
        field = Metafield(name)
        metatype.children.append(field)
        field.orderpos = len(metatype.children) - 1
        db.session.commit()
    # <----- Begin: For fields of list type ----->

    if filenode:
        # all files of the field will be removed before a new file kann be added
        for fnode in field.files:
            field.files.remove(fnode)         # remove the file from the node tree
            try:
                os.remove(fnode.abspath)  # delete the file from the hard drive
            except:
                logg.exception("exception in updateMetaField")
        field.files.append(filenode)

    if fieldvalues.startswith("multiple"):
        field.set("multiple", True)
        fieldvalues = fieldvalues.replace("multiple;", "", 1)
    else:
        if field.get("multiple"):
            del field.attrs["multiple"]

    if fieldvalues.endswith("delete"):  # the checkbox 'delete' was checked
        # all files of the field will be removed
        for fnode in field.files:
            field.files.remove(fnode)         # remove the file from the node tree
            try:
                os.remove(fnode.abspath)  # delete the file from the hard drive
            except:
                logg.exception("exception in updateMetaField")
        fieldvalues = fieldvalues.replace(";delete", "", 1)

    #<----- End: For fields of list type ----->

    field.set("label", label)
    field.set("type", fieldtype)
    field.set("opts", option)
    field.set("valuelist", fieldvalues.replace("\r\n", ";"))
    field.set("valuelistnum", fieldvaluenum)
    field.set("description", description)

    for attr_name, attr_value in attr_dict.items():
        field.set(attr_name, attr_value)
    db.session.commit()


#
# delete metadatafield
#
def deleteMetaField(pid, name):
    metadatatype = getMetaType(pid)
    field = getMetaField(pid, name)
    metadatatype.children.remove(field)

    i = 0
    for field in metadatatype.children.order_by(Node.orderpos):
        field.orderpos = i
        i += 1
    db.session.commit()

#
# change order of metadatafields: move element up/down
#


def moveMetaField(pid, name, direction):
    up, down = -1, -1

    if direction == 1:
        down = int(getMetaField(pid, name).getOrderPos())
    elif direction == -1:
        up = int(getMetaField(pid, name).getOrderPos())

    i = 0
    for field in getMetaType(pid).getChildren().sort_by_orderpos():
        try:
            if i == up:
                pos = i - 1
            elif i == up - 1:
                pos = up
            elif i == down:
                pos = i + 1
            elif i == down + 1:
                pos = down
            else:
                pos = i

            if pos < 0:
                pos = 0
            field.setOrderPos(pos)
            i += 1
        except:  # FIXME: what kind of exception is raised here?
            pass


def generateMask(metatype, masktype="", force=0):
    if force:
        try:
            metatype.children.remove(metatype.children.filter_by(name=masktype).one())
            db.session.commit()
        except:  # if we can't remove the existing mask, it wasn't there, which is ok
            pass

    mask = metatype.children.filter_by(name=masktype).scalar()
    if mask is not None:
        return  # mask is already there- nothing to do!
    else:
        mask = Mask(u"-auto-")
        metatype.children.append(mask)
        i = 0
        for c in metatype.children.order_by(Node.orderpos):
            if c.type != "mask":
                if c.getFieldtype() != "union":
                    field = Maskitem(c.get("label"))
                    field.orderpos = i
                    i += 1
                    mask.children.append(field)
                    field.set("width", "400")
                    field.set("type", "field")
                    field.children.append(c)
    db.session.commit()


def cloneMask(mask, newmaskname):
    def recurse(m1, m2):
        for k, v in m1.attrs.items():
            m2.set(k, v)
        for c1 in m1.children.order_by(Node.orderpos):
            if c1.type in ["mask", "maskitem"]:
                content_class = Node.get_class_for_typestring(c1.type)
                c2 = content_class(name=c1.name)
                c2.orderpos = c1.orderpos
                m2.children.append(c2)
                recurse(c1, c2)
            else:
                m2.children.append(c1)

    p = mask.parents
    if len(p) == 0:
        raise "Mask has no parents"
    if len(p) > 1:
        raise "Mask has more than one parent"
    if mask.type != "mask":
        raise "Not a mask"
    newmask = Mask(newmaskname)
    p[0].children.append(newmask)
    recurse(mask, newmask)
    db.session.commit()


def checkMask(mask, fix=0, verbose=1, show_unused=0):
    if mask.type != "mask":
        if verbose:
            logg.debug("Node %s %s is no mask", mask.id, mask.name)
        return 1
    p = mask.getParents()
    if len(p) > 1:
        if verbose:
            logg.debug("Mask has more than one parent")
        return 1
    if len(p) == 0:
        if verbose:
            logg.debug("Mask has no parents (?)")
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

    def recurse(node, currentparent):
        global error
        if node.type in ["mask", "maskitem"]:
            for field in node.getChildren():
                recurse(field, node)
            return
        fieldsused[node.name] = 1

        if fix and node.get("orderpos"):
            if verbose:
                print "Removing orderpos attribute from node", node.id
            node.set("orderpos", "")

        if currentparent.type != "maskitem":
            if verbose:
                print "Field", node.id, node.name, "is not below a maskitem (parent:", currentparent.id, currentparent.name, ")"
            error += 1
            if fix:
                currentparent.removeChild(node)
            return

        for parent in node.getParents():
            if parent.type == "metadatatype":
                return  # OK
            elif parent.type in ["maskitem", "mask"]:
                pass
            else:
                print "Node", node.id, node.name, "has strange parent", parent.id, parent.name

        error += 1

        if node.name in field2node:
            node2 = field2node[node.name]
            if verbose:
                print "Node", node.id, node.name, "has/had no entry in metadatatypes (but field with name", node.name, "exists there:", node2.id
            c = 0
            if node.get("required") != node2.get("required"):
                if verbose:
                    print "required", node.get("required"), "<->", "required", node2.get("required")
                c += 1
            elif node.get("type") != node2.get("type"):
                if verbose:
                    print "type", node.get("type"), "<->", "type", node2.get("type")
                c += 1
            elif node.get("label") != node2.get("label"):
                if verbose:
                    print "label", node.get("label"), "<->", "label", node2.get("label")
                c += 1
            elif node.get("opts") != node2.get("opts"):
                if verbose:
                    print "opts", node.get("opts"), "<->", "opts", node2.get("opts")
                c += 1
            if c == 0 and fix:
                currentparent.removeChild(node)
                currentparent.addChild(node2)
        else:
            if verbose:
                print "Node", node.id, node.name, "has/had no entry in metadatatypes"
            if fix:
                metatypes.addChild(node)

    recurse(mask, None)
    if show_unused:
        # go through the other masks, too
        for mask2 in masks:
            if mask != mask2:
                recurse(mask2, None)
        # dump all presumably unused fields
        for name, used in fieldsused.items():
            if not used:
                field = metatypes.getChild(name)
                if "s" not in field.get("opts"):
                    print "Unused field:", field.id, field.name
    return error


def showEditor(node, hiddenvalues={}, allowedFields=None):
    result = ""
    fields = node.getType().getMetaFields()

    for field in fields:
        name = field.getName()
        langNames = None
        if field.get("text"):
            langNames = [lang + name for lang in config.languages]
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
        # if field.description != "":
        # _helpLink = """<a href="#" onclick="openPopup(\'/popup_help?pid=""" +
        # field.pid + """&name=""" + field.name + """\', \'\', 400, 250)"><img
        # src="img/tooltip.png" border="0"></a>"""
        if (field.getRequired() > 0):
            result += ('<tr><td align="left">' + field.getLabel() + ': <span class="required">*</span></td>')
        else:
            result += '<tr><td align="left">%s:</td>' % (field.getLabel())
        result += '<td align="left">%s</td></tr>' % (field.getEditorHTML(value, 400, lock))
    result += ('<tr><td>&nbsp;</td><td align="left"><small>(<span class="required">*</span> Pflichtfeld, darf nicht leer sein)</small></td></tr>')
    result += ('<input type="hidden" name="metaDataEditor" value="metaDataEditor">')

    for k, v in hiddenvalues.items():
        result += ("""<input type="hidden" name="%s" value="%s">\n""" % (k, v))
    return result


def parseEditorData(req, node):
    nodes = [node]
    incorrect = False
    defaultlang = translation.lang(req)

    for field in node.metaFields():
        name = field.getName()
        if "%s__%s" % (defaultlang, name) in req.params:
            value = req.params.get("%s__%s" % (defaultlang, name), "? ")
        else:
            value = req.params.get(name, "? ")

        if value != "? ":
            # if (field.getRequired()==1):
            # not empty
            #    if (value==""):
            # error
            #        incorrect = True

            for node in nodes:
                node.set(name, value)

            # elif (field.getRequired()==2):
            # has to be a number
            #    try:
            #        x = float(value)
            #    except:
            # error
            #        incorrect = True

            #    for node in nodes:
            #        node.set(name, value)

            if field.get('type') == "date":
                f = field.getSystemFormat(field.fieldvalues)
                try:
                    date = parse_date(ustr(value), f.getValue())
                except ValueError:
                    date = None
                if date:
                    value = format_date(date, format='%Y-%m-%dT%H:%M:%S')
                    for node in nodes:
                        node.set(name, value)
            else:
                for node in nodes:
                    node.set(name, value)
        else:  # value not in request -> remove attribute
            try:
                node.removeAttribute(field.getName())
            except KeyError:
                pass
    db.session.commit()
    return not incorrect


#
# export metadatascheme
#
def exportMetaScheme(name):
    if name == "all":
        return getNodeXML(q(Metadatatypes).one())
    else:
        return getNodeXML(getMetaType(name))


#
# import metadatatype from file
#
def importMetaSchema(filename):
    n = readNodeXML(filename)
    importlist = list()
    if n.type == "metadatatype":
        importlist.append(n)
    elif n.type == "metadatatypes":
        for ch in n.children:
            importlist.append(ch)

    metadatatypes = q(Metadatatypes).one()
    for m in importlist:
        m.name = u"import-" + m.name
        metadatatypes.children.append(m)
    db.session.commit()


@check_type_arg
class Metadatatype(Node):

    masks = children_rel("Mask")
    metafields = children_rel("Metafield")

    @property
    def description(self):
        return self.get("description")

    def getDescription(self):
        warn("use Metadatatype.description", DeprecationWarning)
        return self.description

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
        if self.getActive() == 0:
            return False
        return True

    def getDatatypes(self):
        return self.get("datatypes").split(", ")

    def setDatatype(self, valuelist):
        self.set("datatypes", ", ".join(["%s" % k for k in valuelist]))

    def getDatatypeString(self):
        return self.get("datatypes")

    def setDatatypeString(self, value):
        self.set("datatypes", ustr(value))

    def getNumFields(self):
        return len(self.getMetaFields())

    def getMetaFields(self, type=None):
        fields = []
        for item in self.children.sort_by_orderpos():
            if item.type == "metafield":
                if not type or type in item.getOption():
                    fields.append(item)
        return fields

    def filter_masks(self, masktype=None, language=None):
        masks = self.masks
        if masktype:
            masks = masks.filter(Mask.a.masktype.astext == masktype)
        if language:
            # return masks with given language
            masks = masks.filter(Mask.a.language.astext == language)
        return masks

    def get_mask(self, name):
        return self.masks.filter_by(name=name).scalar()

    def getMask(self, name):
        warn("use Metadatatype.get_mask instead", DeprecationWarning)
        return self.get_mask(name)

    def getMasks(self, type=None, language=None):
        warn("use Metadatatype.filter_masks instead", DeprecationWarning)
        masks = self.filter_masks(type, language).all()
        if not masks and language:
            masks = self.filter_masks(type, None).all()
        return masks


""" fields for metadata """


@check_type_arg
class Metafield(Node):

    @property
    def label(self):
        return self.get("label")

    @label.setter
    def label(self, value):
        self.set("label", value)

    def getLabel(self):
        warn("use Metafield.label instead", DeprecationWarning)
        return self.label

    def setLabel(self, value):
        warn("use Metafield.label instead", DeprecationWarning)
        self.label = value

    def getSchemaNode(self):
        for p in self.parents:
            if isinstance(p, Metadatatype):
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
        retList = []
        for option in fieldoption:
            if option.value in self.getOption() and option.value != "":
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
        return self.get("valuelist").replace(";", "\r\n")

    def setValues(self, value):
        self.set("valuelist", value)

    def removeValue(self, value):
        self.set("valuelist", self.get("valuelist").replace(value, ""))

    def Sortfield(self):
        return "o" in self.getOption()

    def Searchfield(self):
        return "s" in self.getOption()

    def getValueList(self):
        return self.getValues().split("\r\n")

    def setValuelist(self, valuelist):
        self.set("valuelist", "; ".join(["%s" % k for k in valuelist]))

    def getSystemFormat(self, shortname):
        for option in dateoption:
            if option.getShortName() == shortname:
                return option
        return dateoption[0]

    def getValue(self, node):
        logg.warn("who uses getValue?")
        if self.get("fieldtype") == "date":
            d = self.getSystemFormat(ustr(self.fieldvalues))
            v = node.get(self.name)
            try:
                value = format_date(parse_date(v), d.getValue())
            except ValueError:
                value = v
        else:
            value = node.get(self.name)
        return value

    def getEditorHTML(self, val="", width=400, lock=0, language=None, required=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")
        return t.getEditorHTML(self, val, width, lock, language=language, required=required)

    def getSearchHTML(self, context):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")
        context.field = self
        return t.getSearchHTML(context)

    def getFormattedValue(self, node, language=None):
        try:
            t = getMetadataType(self.getFieldtype())
        except LookupError:
            t = getMetadataType("default")

        return t.getFormattedValue(self, None, None, node, language=language)

# helper class for masks


class MaskType:

    def __init__(self, type, separator="<br/>"):
        self.type = type
        self.separator = separator

    def setType(self, value):
        self.type = value
        db.session.commit()

    def getType(self):
        return self.type

    def setSeparator(self, value):
        self.separator = value
        db.session.commit()

    def getSeparator(self):
        return self.separator


def getMaskTypes(key="."):
    masktypes = {
        "": MaskType("masktype_empty"),
        "edit": MaskType("masktype_edit"),
        "search": MaskType("masktype_search"),
        "shortview": MaskType("masktype_short", ". "),
        "fullview": MaskType("masktype_full"),
        "export": MaskType("masktype_export")
    }
    if key == ".":
        return masktypes
    else:
        if key in masktypes.keys():
            return masktypes[key]
        else:
            return MaskType()


def update_multilang_field(node, field, mdt, req, updated_attrs):
    """TODO: extracted from updateNode(), rework multilang...
    if multilingual textfields were used, their names are
    saved in form en__Name, de__Name, de-AU__Name, en-US__Name etc.
    """
    for item in req.params.keys():
        langPos = item.find('__')
        if langPos != -1 and item[langPos + 2:] == field.name:
            # cut the language identifier (en__, fr__, etc)
            if (req.params.get(unicode(field.id) + '_show_multilang', '') == 'multi'
                    and hasattr(mdt, "language_update")):
                value_old = node.get(field.name)
                value_new = req.params.get(item)
                value = mdt.language_update(value_old, value_new, item[:langPos])
                updated_attrs[field.name] = value
            elif req.params.get(unicode(field.id) + '_show_multilang', '') == 'single':
                if item[0:langPos] == translation.lang(req):
                    new_value = req.params.get(item)
                    updated_attrs[field.name] = new_value
            elif (req.params.get(unicode(field.id) + '_show_multilang', '') == 'multi'
                  and not hasattr(mdt, "language_update")):
                value = mdt.format_request_value_for_db(field, req.params, item)
                oldValue = node.get(field.name)
                position = oldValue.find(item[:langPos] + mdt.joiner)
                if position != -1:
                    # there is already a value for this language
                    newValue = (oldValue[:position + langPos + len(mdt.joiner)]
                                + value
                                + oldValue[oldValue.find(mdt.joiner,
                                                         position + langPos + len(mdt.joiner)):])
                    updated_attrs[field.name] = newValue
                else:  # there is no value for this language yet
                    if oldValue.find(mdt.joiner) == -1:
                        # there are no values at all yet
                        updated_attrs[field.name] = item[:langPos] + mdt.joiner + value + mdt.joiner
                    else:
                        # there are some values for other languages, but not for the current
                        updated_attrs[field.name] = oldValue + item[:langPos] + mdt.joiner + value + mdt.joiner


@check_type_arg
class Mask(Node):

    maskitems = children_rel("Maskitem", lazy="joined", order_by="Maskitem.orderpos")

    _metadatatypes = parents_rel("Metadatatype")

    @property
    def masktype(self):
        return self.get("masktype")

    @property
    def language(self):
        return self.get("language")

    @hybrid_property
    def metadatatype(self):
        return self._metadatatypes.scalar()

    @metadatatype.expression
    def metadatatype_expr(cls):
        class MetadatatypeExpr(object):
            def __eq__(self, other):
                return cls._metadatatypes.contains(other)

        return MetadatatypeExpr()


    @property
    def all_maskitems(self):
        """Recursively get all maskitems, they can be nested
        """
        return self.all_children_by_query(q(Maskitem))

    def getFormHTML(self, nodes, req):
        if not self.children:
            return None

        ret = ''
        for field in self.children.sort_by_orderpos():
            t = getMetadataType(field.get("type"))
            ret += t.getFormHTML(field, nodes, req)
        return ret

    def getViewHTML(self, nodes, flags=0, language=None, template_from_caller=None):
        if flags & 4:
            ret = []
        else:
            ret = ""

        if flags & 8:  # export mode
            x = self.getChildren()
            x.sort_by_orderpos()
            return getMetadataType("mappingfield").getViewHTML(
                x, nodes, flags, language=language, template_from_caller=template_from_caller, mask=self)
        for maskitem in self.maskitems:
            t = getMetadataType(maskitem.get("type"))
            if flags & 4:  # data mode
                v = t.getViewHTML(maskitem, nodes, flags, language=language, template_from_caller=template_from_caller, mask=self)
                format = maskitem.getFormat()
                if format != "":
                    v[1] = format.replace("<value>", v[1])
                v.append(maskitem.getSeparator())

                if flags & 2:   # hide empty
                    if v[1].strip() != "":
                        ret.append(v)
                else:
                    ret.append(v)
            else:
                ret += t.getViewHTML(maskitem, nodes, flags, language=language, template_from_caller=template_from_caller, mask=self)
        return ret

    def getViewList(self, node, flags=0, language=None):
        if not self.getChildren():
            return None
        if flags & 4:
            ret = []
        else:
            ret = ''
        for field in self.getChildren().sort_by_orderpos():
            t = getMetadataType(field.get("type"))
            if flags & 4:
                ret.append(t.getViewHTML(field, node, flags, language=language))
            else:
                ret += t.getViewHTML(field, node, flags, language=language)
        return ret

    def getMaskFields(self, first_level_only=False):
        warn("use Mask.maskitems or Mask.all_maskitems instead", DeprecationWarning)
        # XXX: type changed: list -> NodeAppenderQuery
        if first_level_only:
            return self.maskitems
        else:
            return self.all_maskitems

    """ return all fields which are empty """

    def validate(self, nodes):
        ret = []
        for node in nodes:
            for item in self.getMaskFields():
                field = item.getField()
                if item.getRequired() == 1:
                    if node.get(field.getName()) == "":
                        ret.append(field.id)

                if field and field.getContentType() == "metafield" and field.getFieldtype() == "date":
                    if not node.get(field.getName()) == "" and not validateDateString(node.get(field.getName())):
                        ret.append(field.id)
        return ret

    """ return all node ids which are empty """

    def validateNodelist(self, nodes):
        ret = []
        for node in nodes:
            for item in self.getMaskFields():
                field = item.getField()
                if item.getRequired() == 1:
                    if node.get(field.getName()) == "":
                        ret.append(node.id)
                        logg.error("Error in publishing of node %r: The required field %r is empty." ,node.id, field.name)

                if field and field.getContentType() == "metafield" and field.getFieldtype() == "date":
                    if not node.get(field.getName()) == "":
                        if field.name == "yearmonth":
                            try:
                                datetime.datetime.strptime(node.get(field.getName())[:7], '%Y-%m')
                            except ValueError:
                                ret.append(node.id)
                                logg.error("Error in publishing of node %r: The date field 'yearmonth' with content %r is not valid.",
                                    node.id, node.get(field.getName()))
                            continue
                        if not validateDateString(node.get(field.getName())):
                            ret.append(node.id)
                            logg.error("Error in publishing of node %r: The date field %r with content %r is not valid.",
                                (node.id, field.name, node.get(field.getName())))
        return ret

    ''' returns True if all mandatory fields of mappingdefinition are used -> valid format'''

    def validateMappingDef(self):
        mandfields = []
        if self.getMasktype() == "export":
            for mapping in self.get("exportmapping").split(";"):
                for c in q(Node).get(mapping).getMandatoryFields():
                    mandfields.append(c.id)
        for item in self.all_maskitems:
            try:
                mandfields.remove(item.get("mappingfield"))
            except ValueError:  # id not in list
                pass
        return len(mandfields) == 0


    def update_node(self, node, req, user):
        ''' update given node with given request values '''
        form = req.form
        # collect all changes first and apply them at the end because SQLAlchemy would issue an UPDATE for each attr assignment
        updated_attrs = {}
        updated_system_attrs = {}
        for item in self.all_maskitems:
            field = item.metafield

            if field and form.get(field.name, "").find("?") != 0:
                t = getMetadataType(field.get("type"))

                if field.name in form:
                    if field.name == 'nodename':
                        value = form.get('nodename')
                        node.name = value
                    else:
                        value = t.format_request_value_for_db(field, form, field.name)
                        if field.name.startswith("system."):
                            updated_system_attrs[field.name[len("system."):]] = value
                        else:
                            updated_attrs[field.name] = value

                elif field["type"] == "check":
                    updated_attrs[field.name] = "0"

                # handle multilang heritage
                elif field.name == 'nodename' and translation.getDefaultLanguage() + '__nodename' in form:
                    value = form.get(translation.getDefaultLanguage() + '__nodename')
                    node.name = value
                    update_multilang_field(node, field, t, req, updated_attrs)

                else:
                    update_multilang_field(node, field, t, req, updated_attrs)

                if hasattr(t, "event_metafield_changed"):
                    t.event_metafield_changed(node, field)

        updated_attrs["updateuser"] = user.getName()
        updated_attrs["updatetime"] = format_date()

        node.attrs.update(updated_attrs)
        node.system_attrs.update(updated_system_attrs)

        if hasattr(node, "event_metadata_changed"):
            node.event_metadata_changed()

    def getMappingHeader(self):
        from .mapping import Mapping
        if self.getMasktype() == "export":
            if len(self.get("exportheader")) > 0:
                return self.get("exportheader")
            elif len(self.get("exportmapping").split(";")) > 1:
                return self.getExportHeader()
            else:
                exportmapping_id = self.get("exportmapping")
                c = q(Mapping).get(exportmapping_id)
                if c is not None:
                    return c.getHeader()
                else:
                    logg.warn("exportmapping %s for mask %s not found", exportmapping_id, self.id)
                    return u""
        return u""

    def getMappingFooter(self):
        from .mapping import Mapping
        if self.getMasktype() == "export":
            if len(self.get("exportfooter")) > 0:
                return self.get("exportfooter")
            elif len(self.get("exportmapping").split(";")) > 1:
                return self.getExportFooter()
            else:
                c = q(Mapping).get(self.get("exportmapping"))
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
        ret += unicode(self.id)
        ret += '" i18n:attributes="title mask_editor_new_line_title"/></div><br/>'

        if not self.validateMappingDef():
            ret += '<p i18n:translate="mask_editor_export_error" class="error">TEXT</p>'

        if len(self.children) == 0:
            ret += '<div i18n:translate="mask_editor_no_fields">- keine Felder definiert -</div>'
        else:
            if self.getMappingHeader() != "":
                ret += '<div class="label" i18n:translate="mask_edit_header">TEXT</div><div class="row">%s</div>' % (
                    esc(self.getMappingHeader()))

        # check if all the orderpos attributes are the same which causes problems with sorting
        z = [t for t in self.children.order_by(Node.orderpos)]
        if all(z[0].orderpos == item.orderpos for item in z):
            k = 0
            for elem in z:
                elem.orderpos = elem.orderpos + k
                k += 1

        i = 0
        fieldlist = {}  # !!!getAllMetaFields()
        for item in self.children.order_by(Node.orderpos):
            t = getMetadataType(item.get("type"))
            ret += t.getMetaHTML(self, i, language=language, fieldlist=fieldlist)  # get formated line specific of type (e.g. field)
            i += 1

        if len(self.children) > 0:
            if self.getMappingFooter() != "":
                ret += '<div class="label" i18n:translate="mask_edit_footer">TEXT</div><div class="row">%s</div>' % (
                    esc(self.getMappingFooter()))
        ret += '</form>'
        return ret

    """ """

    def editItem(self, req):
        for key in req.params.keys():
            # edit field
            if key.startswith("edit_"):
                item = q(Node).get(req.params.get("edit", ""))
                t = getMetadataType(item.get("type"))
                return '<form method="post" name="myform">%s</form>' % (t.getMetaEditor(item, req))

        if (req.params.get("op", "") == "new" and req.params.get("type", "") != "") or (
                self.getMasktype() == "export" and req.params.get("op", "") in ["newdetail", "new"]):
            # add field
            item = Maskitem(u'')
            db.session.add(item)
            if self.getMasktype() == "export":  # export mask has no selection of fieldtype -> only field
                t = getMetadataType("field")
                req.params["op"] = "new"
            else:
                t = getMetadataType(req.params.get("type"))

            if req.params.get("type", "") in ["hgroup", "vgroup"]:
                req.params["edit"] = item
            else:
                req.params["edit"] = item.id
            return u'<form method="post" name="myform">{}</form>'.format(t.getMetaEditor(item, req))

        if (req.params.get("type", "") == "" and self.getMasktype() != "export") or req.params.get('op') == 'newdetail':
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
            ret += '<input type="hidden" name="pid" value="' + req.params.get("pid") + '"/>'
            ret += '<div class="label">&nbsp;</div><button type="submit" name="new_" style="width:100px" i18n:translate="mask_editor_ok"> OK </button>'
            ret += '&nbsp;&nbsp;<button type="submit" onclick="setCancel(document.myform.op)" i18n:translate="mask_editor_cancel">Abbrechen</button><br/>'
            ret += '</div></form>'
            return req.getTALstr(ret, {})

        if req.params.get("edit", " ") == " " and req.params.get("op", "") != "new":
            # create new node
            item = q(Node).get(req.params.get("id"))
            t = getMetadataType(req.params.get("type"))
            return '<form method="post" name="myform">%s</form>' % (t.getMetaEditor(item, req))

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
        return self.get("language")

    def setLanguage(self, value):
        self.set("language", value)

    def getDefaultMask(self):
        if self.get("defaultmask") == "True":
            return True
        return False

    def setDefaultMask(self, value):
        if value:
            self.set("defaultmask", "True")
        else:
            self.set("defaultmask", "False")

    def getSeparator(self):
        for key, value in self.attrs.items():
            if key == "separator":
                return self.get("separator")
        return getMaskTypes(self.getMasktype()).getSeparator()

    def setSeparator(self, value):
        self.set("separator", value)

    def addMaskitem(self, label, type, fieldid, pid):
        item = Maskitem(label)
        item.set("type", type)

        if fieldid != 0:
            for id in ustr(fieldid).split(";"):
                try:
                    field = q(Node).get(long(id))
                    # don't remove field- it may
                    # (a) be used for some other mask item or
                    # (b) still be in the global metadatafield list
                    # for p in field.getParents():
                    #    p.removeChild(field)
                    item.children.append(field)
                except ValueError:
                    print "node id error for id '", id, "'"
        if ustr(pid) == "0":
            self.children.append(item)
        else:
            node = q(Node).get(pid)
            node.children.append(item)
        db.session.commit()
        return item

    ''' delete given  maskitem '''

    def deleteMaskitem(self, itemid):
        item = q(Node).get(itemid)
        for parent in item.parents:
            parent.children.remove(item)
            i = 0
            for child in parent.children.order_by(Node.orderpos):
                child.orderpos = i
                i += 1
        db.session.commit()

""" class for editor/view masks """


@check_type_arg
class Maskitem(Node):

    _metafield_rel = children_rel("Metafield", backref="maskitems", lazy="joined")

    @property
    def metafield(self):
        return self._metafield_rel[0] if self._metafield_rel else None

    @metafield.setter
    def metafield(self, metafield):
        if metafield is None:
            raise ValueError("setting metafield to None is not allowed!")

        self._metafield_rel = [metafield]

    def getLabel(self):
        return self.getName()

    def setLabel(self, value):
        self.name = value

    def getField(self):
        warn("use Maskitem.metafield", DeprecationWarning)
        try:
            return self.metafield
        except NoResultFound:
            return None

    def getDescription(self):
        if not self.get("description") and self.getField():
            return self.getField().getDescription()
        else:
            return self.get("description")

    def setDescription(self, value):
        if not self.get("description") and self.getField():
            self.getField().setDescription(value)
        else:
            self.set("description", value)

    def getRequired(self):
        if self.get("required"):
            return int(self.get("required"))
        else:
            return 0

    def setRequired(self, value):
        self.set("required", value)

    def getWidth(self):
        if self.get("width"):
            return int(self.get("width"))
        else:
            return 400

    def setWidth(self, value=u'400'):
        self.set("width", value)

    def getDefault(self):
        return self.get("default")

    def setDefault(self, value):
        self.set("default", value)

    def getTestNodes(self):
        return self.get("testnodes")

    def setTestNodes(self, value):
        self.set("testnodes", value)

    def getMultilang(self):
        field = [c for c in self.getChildren() if c.type == "metafield"]
        if len(field) > 0:
            if field[0].get("multilang"):
                return 1
        return 0

    def setMultilang(self, value):
        field = [c for c in self.getChildren() if c.type == "metafield"]
        if len(field) > 0:
            field[0].set("multilang", value)

    def getUnit(self):
        # XXX: we don't want empty units, better sanitize user input instead of stripping here
        return self.get("unit").strip()

    def setUnit(self, value):
        self.set("unit", value)

    def getFormat(self):
        return self.get("format")

    def setFormat(self, value):
        self.set("format", value)

    def getSeparator(self):
        return self.get("separator") or ""

    def setSeparator(self, value):
        self.set("separator", value)


mytypes = {}


def _metatype_class(name, cls):
    name = name[2:] if name.startswith("m_") else name
    logg.debug("loading metatype class %s", name)
    instance = cls()
    mytypes[name] = instance
    if hasattr(instance, "getLabels"):
        translation.addLabels(instance.getLabels())


def load_metatype_module(prefix_path, pkg_dir):
    logg.debug("loading modules from '%s', prefix path %s", pkg_dir, prefix_path)
    if prefix_path not in sys.path:
        logg.debug("%s added to pythonpath", prefix_path)
        sys.path.append(prefix_path)
    for _, name, _ in pkgutil.iter_modules([os.path.join(prefix_path, pkg_dir)]):
        module = importlib.import_module(pkg_dir.replace("/", ".") + "." + name)

        def is_metatype_class(obj):
            return inspect.isclass(obj) and issubclass(obj, Metatype) and obj.__name__ != "Metatype"
        for name, cls in inspect.getmembers(module, is_metatype_class):
            _metatype_class(name, cls)


def init():
    pkg_dirs = ["schema/mask", "metadata"]
    for pkg_dir in pkg_dirs:
        load_metatype_module(config.basedir, pkg_dir)


def getMetadataType(mtype):
    if mtype in mytypes:
        return mytypes[mtype]
    else:
        raise LookupError("No such metatype: " + mtype)


def getMetaFieldTypeNames():
    ret = {}
    for key in mytypes.keys():
        if "meta" in ustr(mytypes[key]):
            ret[key] = "fieldtype_" + key
    return ret


def getMetaFieldTypes():
    ret = {}
    for t in mytypes:
        if getMetadataType(t).isFieldType():
            ret[t] = getMetadataType(t)
    return ret

""" return fields based on the schema name """


def getFieldsForMeta(name):
    return list(getMetaType(name).getMetaFields())


class SchemaMixin(object):

    def getMask(self, name):
        warn("use Default.metadatatype.get_mask instead", DeprecationWarning)
        mdt = self.metadatatype
        return mdt.get_mask(name)

    def getMasks(self, type=None, language=None):
        warn("use Default.metadatatype.filter_masks instead", DeprecationWarning)
        return self.metadatatype.getMasks(type, language)

    def getFullView(self, language):
        """Gets the fullview mask for the given `language`.
        If no matching language mask is found, return a mask without language specification or None.
        :rtype: Mask
        """
        
        from sqlalchemy.orm import joinedload
        
        mask_load_opts = (undefer("attrs"), 
                          joinedload(Mask.maskitems).undefer("attrs").joinedload(Maskitem._metafield_rel).undefer("attrs"))

        lang_mask = self.metadatatype.filter_masks(masktype=u"fullview", language=language).options(mask_load_opts).first()

        if lang_mask is not None:
            return lang_mask
        else:
            return self.metadatatype.filter_masks(masktype=u"fullview").options(mask_load_opts).first()

    @cached_property
    def metadatatype(self):
        try:
            return q(Metadatatype).filter_by(name=self.schema).one()
        except NoResultFound:
            raise Exception("metadatatype '{}' is missing, needed for node {}".format(self.schema, self))

    def getSchema(self):
        warn("deprecated, use Content.schema instead", DeprecationWarning)
        return self.schema

    def getMetaFields(self, type=None):
        """return fields based on node class and schema name
        """
        try:
            l = self.metaFields()
        except:
            l = []

        try:
            if self.getSchema():
                l += getMetaType(self.getSchema()).getMetaFields(type)
        except AttributeError:
            pass
        return l

    def getSearchFields(self):
        sfields = []
        fields = self.getMetaFields()
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))
        for field in fields:
            if field.Searchfield():
                sfields += [field]
        return sfields

    def getSortFields(self):
        sfields = []
        fields = self.getMetaFields()
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))
        for field in fields:
            if field.Sortfield():
                sfields += [field]
        return sfields

    def getDescription(self):
        if self.getSchema():
            mtype = getMetaType(self.getSchema())
            if mtype:
                return mtype.getDescription()
            else:
                return ""
