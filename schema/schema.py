# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import collections as _collections
import datetime
import functools as _functools
import inspect
import importlib
import itertools as _itertools
import logging
import os
import pkgutil
import sys
import collections as _collections
from warnings import warn

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import undefer
import sqlalchemy as _sqlalchemy
from werkzeug.utils import cached_property
import core.config as config
import core.csrfform as _core_csrfform
import core.translation as translation
from core import Node
from core.xmlnode import getNodeXML, readNodeXML
from core.metatype import Metatype
from core import db
import core.nodecache as _nodecache
from core.systemtypes import Metadatatypes
from core.postgres import check_type_arg
from core.database.postgres.node import children_rel, parents_rel
from utils.date import parse_date, format_date, validateDateString
from utils.utils import esc, suppress
import utils as _utils
from mediatumtal import tal as _tal
import core.database.postgres.node as _node


log = logg = logging.getLogger(__name__)
q = db.query


_Option = _functools.partial(
    _collections.namedtuple(
        "_Option",
        "name shortname value imgsource optiontype validation_regex",
    ), imgsource='', optiontype='', validation_regex='',
)


requiredoption = (
    _Option(
        name="Kein Pflichtfeld",
        shortname="notmandatory",
        value="0",
        imgsource="/img/req2_opt.png",
    ),
    _Option(
        name="Pflichtfeld, darf nicht leer sein",
        shortname="mandatory1", value="1",
        imgsource="/img/req0_opt.png",
    ),
    _Option(
        name="Pflichtfeld, muss eine Zahl sein",
        shortname="mandatory2",
        value="2",
        imgsource="/img/req1_opt.png",
    ),
)

fieldoption = (
    _Option(
        name="metafield_option1",
        shortname="search", value="s",
        imgsource="/img/folder_plus.gif",
    ),
    _Option(
        name="metafield_option2",
        shortname="sort",
        value="o",
        imgsource="/img/ordersel.png",
    ),
)

dateoption = (
    _Option(
        name="metafield_dateformat_std",
        shortname="dd.mm.yyyy",
        value="%d.%m.%Y",
        validation_regex='^(0[0-9]|1[0-9]|2[0-9]|3[01])\.(0[0-9]|1[012])\.[0-9]{4}$',
    ),
    _Option(
        name="metafield_dateformat_long",
        shortname="dd.mm.yyyy hh:mm:ss",
        value="%d.%m.%Y %H:%M:%S",
        validation_regex='^(0[0-9]|1[0-9]|2[0-9]|3[01])\.(0[0-9]|1[012])\.[0-9]{4} (0[0-9]|1[0-9]|2[0-3])(:[0-5][0-9]){2}$',
    ),
    _Option(
        name="metafield_dateformat_year",
        shortname="yyyy",
        value="%Y",
        validation_regex='^[0-9]{4}$',
    ),
    _Option(
        name="metafield_dateformat_yearmonth",
        shortname="yyyy-mm",
        value="%Y-%m",
        validation_regex='^[0-9]{4}-(0[0-9]|1[012])$',
    ),
    _Option(
        name="metafield_dateformat_month",
        shortname="mm",
        value="%m",
        validation_regex='^(0[0-9]|1[012])$',
    ),
    _Option(
        name="metafield_dateformat_time",
        shortname="hh:mm:ss",
        value="%H:%M:%S",
        validation_regex='^(0[0-9]|1[0-9]|2[0-3])(:[0-5][0-9]){2}$',
    ),
)

VIEW_DEFAULT = 0        # default view for masks
VIEW_SUB_ELEMENT = 1    # internal parameter
VIEW_HIDE_EMPTY = 2     # show only fields with 'non-empty' values
VIEW_DATA_ONLY = 4      # deliver list with values (not html)
VIEW_DATA_EXPORT = 8    # deliver export format

_EditUpdateAttrs = _collections.namedtuple("edit_update_attrs", "nodename fields attrs system_attrs")

_MetafieldsDependency = _collections.namedtuple(
    "_MetafieldsDependency",
    "metadatatypes_id schema_name mask_name maskitem_name metafield_name metafield_id"
)


def _get_metafields_dependencies():
    """
    collect a list of all metafields together with metadatatype and mask and maskitems to which the metafield belongs
    :return: list of _MetafieldsDependency
    """
    metadatatype, mask, maskitem, metafield = (
        _sqlalchemy.orm.aliased(_node.Node) for _ in xrange(4))

    query = q(
        Metadatatypes.id.label('metadatatypes_id'),
        metadatatype.name.label('schema_name'),
        mask.name.label('mask_name'),
        maskitem.name.label('maskitem_name'),
        metafield.name.label('metafield_name'),
        metafield.id.label('metafield_id'),
    )

    joins = (
        Metadatatypes,
        metadatatype,
        mask,
        maskitem,
        metafield,
    )

    for parent, child in zip(joins[:-1], joins[1:]):
        # maskitems can be nested, which means that a masktitem can have another maskitem as child
        # so use noderelation for maskitems to get all childs instead of nodemapping
        node2node = _node.t_noderelation if (parent, child) == (mask, maskitem) else _node.t_nodemapping
        noderelation = _sqlalchemy.orm.aliased(node2node)
        query = query.join(noderelation, noderelation.c.nid == parent.id)
        query = query.join(child, child.id == noderelation.c.cid)
    return tuple(_MetafieldsDependency(**row._asdict()) for row in query.all())

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

    return _nodecache.get_metadatatypes_node().children.filter_by(name=name).scalar()

#
# load all meta-types from db
#

def loadTypesFromDB():
    warn("use q(Metadatatypes) instead", DeprecationWarning)
    # do not use list(q(Metadatatype).order_by("name")) which reports also deleted nodes from type metadatatype
    return list(_nodecache.get_metadatatypes_node().children.order_by("name"))

def get_permitted_schemas():
    metadatatypes = _nodecache.get_metadatatypes_node()
    return metadatatypes.children.filter(Metadatatype.a.active == "1").filter_read_access().order_by(Metadatatype.a.longname).all()

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
    metadatatypes = _nodecache.get_metadatatypes_node()
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


def delete_mask(mask):
    """
    delete all maskitems of mask and the mask itself
    :param mask:
    :return:
    """
    for maskitem in mask.children:
        mask.deleteMaskitem(maskitem.id)
    db.session.delete(mask)


def _delete_metadatatype_children(metadatatype):
    """
    delete all masks and metafields of metadatatype
    :param metadatatype:
    :return:
    """
    for mask in metadatatype.children.filter_by(type='mask'):
        delete_mask(mask)
    for metafield in metadatatype.children.filter_by(type='metafield'):
        deleteMetaField(str(metadatatype.id), metafield.name)


def _delete_metadatatype(metadatatype):
    """
    delete a metadatatype together with its children
    :param metadatatype:
    :return:
    """
    _delete_metadatatype_children(metadatatype)
    db.session.delete(metadatatype)

#
# delete metatype by given name
#

def deleteMetaType(name):
    """
    delete all metadatatypes with name=name together with their children
    metadatatypes which are children of Metadatatypes are unlinked from
    Metadatatypes
    :param name:
    :return:
    """
    for metadatatype in q(Metadatatype).filter_by(name=name).all():
        _delete_metadatatype(metadatatype)
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
    return metatype.children.filter_by(name=name).filter(Node.type=="metafield").scalar()

#
# check existance of field for given metadatatype
#
def existMetaField(pid, name):
    return getMetaField(pid, name) is not None

""" update/create metadatafield """

def updateMetaField(
        parent,
        name,
        label,
        fieldtype,
        option,
        description,
        fieldvalues,
        fieldid,
       ):
    metatype = getMetaType(parent)

    # search the field by id, then by name,
    # or create a new one if both searches didn't yield a result
    field = None
    if fieldid:
        field = q(Node).get(fieldid)
    if field is not None:
        field.name = name
    else:
        field = metatype.children.filter_by(name=name).filter(Node.type=="metafield").scalar()
    if not field:
        field = Metafield(name)
        metatype.children.append(field)
        field.orderpos = len(metatype.children) - 1
        db.session.commit()
    # <----- Begin: For fields of list type ----->
    if fieldvalues.startswith("multiple"):
        field.set("multiple", True)
        fieldvalues = fieldvalues.replace("multiple;", "", 1)
    else:
        if field.get("multiple"):
            del field.attrs["multiple"]
    #<----- End: For fields of list type ----->

    field.set("label", label)
    field.set("type", fieldtype)
    field.set("opts", "".join(option))
    field.set("valuelist", fieldvalues.replace("\r\n", ";"))
    field.set("description", description)

    db.session.commit()

#
# delete metadatafield
#
def deleteMetaField(pid, name):
    metadatatype = getMetaType(pid)
    field = getMetaField(pid, name)
    db.session.delete(field)

    i = 0
    for field in metadatatype.children.filter(Node.type == 'metafield').order_by(Node.orderpos):
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
        with suppress(Exception): # FIXME: what kind of exception is raised here?
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

def generateMask(metatype, masktype="", force=0):
    if force:
        with suppress(Exception, warn=False): # if we can't remove the existing mask, it wasn't there, which is ok
            metatype.children.remove(metatype.children.filter_by(name=masktype).one())
            db.session.commit()

    mask = metatype.children.filter_by(name=masktype).scalar()
    if mask is not None:
        return  # mask is already there- nothing to do!
    mask = Mask(u"-auto-")
    metatype.children.append(mask)
    for i, c in enumerate(metatype.children.filter(Node.type!='mask').order_by(Node.orderpos)):
        field = Maskitem(c.get("label"))
        field.orderpos = i
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
                logg.info("Removing orderpos attribute from node %s", node.id)
            node.set("orderpos", "")

        if currentparent.type != "maskitem":
            if verbose:
                logg.info("Field %s %s is not below a maskitem (parent: %s %s)", node.id, node.name, currentparent.id, currentparent.name)
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
                logg.warn("Node %s %s has strange parent %s %s", node.id, node.name, parent.id, parent.name)

        error += 1

        if node.name in field2node:
            node2 = field2node[node.name]
            if verbose:
                logg.info("Node %s %s has/had no entry in metadatatypes (but field with name %s exists there: %s",
                    node.id, node.name, node.name, node2.id
                )
            c = 0
            if node.get("required") != node2.get("required"):
                if verbose:
                    logg.info("required %s <-> required %s", node.get("required"), node2.get("required"))
                c += 1
            elif node.get("type") != node2.get("type"):
                if verbose:
                    logg.info("type %s <-> type %s", node.get("type"), node2.get("type"))
                c += 1
            elif node.get("label") != node2.get("label"):
                if verbose:
                    logg.info("label %s <-> label %s", node.get("label"), node2.get("label"))
                c += 1
            elif node.get("opts") != node2.get("opts"):
                if verbose:
                    logg.info("opts %s <-> opts %s", node.get("opts"), node2.get("opts"))
                c += 1
            if c == 0 and fix:
                currentparent.removeChild(node)
                currentparent.addChild(node2)
        else:
            if verbose:
                logg.info("Node %s %s has/had no entry in metadatatypes", node.id, node.name)
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
                    logg.debug("Unused field: %s %s", field.id, field.name)
    return error


def parseEditorData(req, node):
    nodes = [node]
    incorrect = False
    defaultlang = translation.set_language(req.accept_languages)

    for field in node.metaFields():
        name = field.getName()
        if "%s__%s" % (defaultlang, name) in req.params:
            value = req.params.get("%s__%s" % (defaultlang, name), "? ")
        else:
            value = req.params.get(name, "? ")

        if value != "? ":
            for node in nodes:
                node.set(name, value)

            if field.get('type') == "date":
                f = field.getSystemFormat(field.fieldvalues)
                try:
                    date = parse_date(ustr(value), f.value)
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
            with suppress(KeyError, warn=False):
                node.removeAttribute(field.getName())
    db.session.commit()
    return not incorrect


#
# export metadatascheme
#
def exportMetaScheme(name):
    if name == "all":
        return getNodeXML(_nodecache.get_metadatatypes_node())
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

    metadatatypes = _nodecache.get_metadatatypes_node()
    for m in importlist:
        m.name = u"{}_import_{}".format(m.name, _utils.utils.gen_secure_token(128))
        if not metadatatypes.children.filter_by(name=m.name).all():
            metadatatypes.children.append(m)
    db.session.commit()


@check_type_arg
class Metadatatype(Node):

    masks = children_rel("Mask")
    metafields = children_rel("Metafield", viewonly=True)

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
        for item in self.children.sort_by_orderpos().prefetch_attrs():
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
            if option.shortname == shortname:
                return option
        return dateoption[0]

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


@check_type_arg
class Mask(Node):

    maskitems = children_rel("Maskitem", lazy="joined", order_by="Maskitem.orderpos", viewonly=True)

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

    def set_default_metadata(self, node):
        """
        create all metadata and set it to default value according mask (normally editmask) if they are
        missing in the document
        called if the document is uploaded via bibtex- or doi-import
        :param node: document uploaded view bibtex- or doi-import
        :return: None
        """
        if not self.children:
            return None

        for field in self.children.sort_by_orderpos():
            t = getMetadataType(field.get("type"))
            if hasattr(t, "set_default_metadata"):
                t.set_default_metadata(field, node)

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
                        logg.error("Error in publishing of node %s: The required field %s is empty.", node.id, field.name)

                if field and field.getContentType() == "metafield" and field.getFieldtype() == "date":
                    if not node.get(field.getName()) == "":
                        if field.name == "yearmonth":
                            try:
                                datetime.datetime.strptime(node.get(field.getName())[:7], '%Y-%m')
                            except ValueError:
                                ret.append(node.id)
                                logg.error(
                                    "Error in publishing of node %s: The date field 'yearmonth' with content %s is not valid.",
                                    node.id,
                                    node.get(field.getName()),
                                )
                            continue
                        if not validateDateString(node.get(field.getName())):
                            ret.append(node.id)
                            logg.error(
                                "Error in publishing of node %s: The date field %s with content %s is not valid.",
                                node.id,
                                field.name,
                                node.get(field.getName()),
                            )
        return ret

    ''' returns True if all mandatory fields of mappingdefinition are used -> valid format'''

    def validateMappingDef(self):
        mandfields = []
        if self.getMasktype() == "export" and self.get("exportmapping"):
            for mapping in self.get("exportmapping").split(";"):
                for c in q(Node).get(mapping).getMandatoryFields():
                    mandfields.append(c.id)
        for item in self.all_maskitems:
            with suppress(ValueError, warn=False):   # id not in list
                mandfields.remove(item.get("mappingfield"))
        return len(mandfields) == 0

    def get_edit_update_attrs(self, req, user):
        """
        Computes and returns a structure that contains all to-be-updated attributes, independent of a node
        :param req:
        :param user:
        :return: attributes to update
        """
        assert self.masktype == "edit"
        form = req.form
        attrs = {}
        system_attrs = {}
        nodename = None
        fields = list()
        current_language = translation.set_language(req.accept_languages)
        default_language = config.languages[0]
        for item in self.all_maskitems:
            field = item.metafield
            if field and form.get(field.name, "").find("?") != 0:
                t = getMetadataType(field.get("type"))
                if field.name in form:
                    if field.name == 'nodename':
                        value = form.get('nodename')
                        nodename = value
                    else:
                        value = t.format_request_value_for_db(field, form, field.name)
                        if field.name.startswith("system."):
                            system_attrs[field.name[len("system."):]] = value
                        else:
                            attrs[field.name] = value
                elif field["type"] == "check":
                    attrs[field.name] = "0"
                # handle multilang heritage
                elif field.name == 'nodename':
                    if default_language + '__nodename' in form:
                        value = form.get(default_language + '__nodename')
                        nodename = value
                    elif current_language + '__nodename' in form:
                        value = form.get(current_language + '__nodename')
                        nodename = value
                fields.append(field)

        system_attrs["edit.lastmask"] = self.name
        attrs["updateuser"] = user.getName()
        attrs["updatetime"] = format_date()

        return _EditUpdateAttrs(nodename, fields, attrs, system_attrs)

    def apply_edit_update_attrs_to_node(self, node, attrs):
        """
        Uses the precomputed structure to update a single node
        :param node: node to be updated
        :param attrs: attributes to update
        :return:
        """
        for field in attrs.fields:
            t = getMetadataType(field.get("type"))
            if hasattr(t, "event_metafield_changed"):
                t.event_metafield_changed(node, field)

        if attrs.nodename and node.name != attrs.nodename:
            node.name = attrs.nodename

        node.attrs.update(attrs.attrs)
        node.system_attrs.update(attrs.system_attrs)

        if hasattr(node, "event_metadata_changed"):
            node.event_metadata_changed()

    def getMappingHeader(self):
        from .mapping import Mapping
        if self.getMasktype() != "export":
            return u""
        if len(self.get("exportheader")) > 0:
            return self.get("exportheader")
        if len(self.get("exportmapping").split(";")) > 1:
            return self.getExportHeader()
        exportmapping_id = self.get("exportmapping")
        if not exportmapping_id:
            return
        c = q(Mapping).get(exportmapping_id)
        if c is not None:
            return c.getHeader()
        logg.warn("exportmapping %s for mask %s not found", exportmapping_id, self.id)
        return u""

    def getMappingFooter(self):
        from .mapping import Mapping
        if self.getMasktype() != "export":
            return ""
        if len(self.get("exportfooter")) > 0:
            return self.get("exportfooter")
        if len(self.get("exportmapping").split(";")) > 1:
            return self.getExportFooter()
        exportmapping_id = self.get("exportmapping")
        if not exportmapping_id:
            return
        c = q(Mapping).get(exportmapping_id)
        if c is not None:
            return c.getFooter()
        logg.warn("exportmapping %s for mask %s not found", exportmapping_id, self.id)
        return u""

    ''' show maskeditor - definition '''

    def getMetaMask(self, req):
        language = translation.set_language(req.accept_languages)
        ret = '<form method="post" name="myform">'
        ret += '<input value="' + _core_csrfform.get_token() + '" type="hidden" name="csrf_token">'
        ret += '<div class="back"><h3 i18n:translate="mask_editor_field_definition">Felddefinition </h3>'
        ret += '<div align="right"><input type="image" src="/img/install.png" name="newdetail_'
        ret += unicode(self.id)
        ret += '" i18n:attributes="title mask_editor_new_line_title"/></div><br/>'

        if not self.validateMappingDef():
            ret += '<p i18n:translate="mask_editor_export_error" class="error">TEXT</p>'

        if len(self.children) == 0:
            ret += '<div i18n:translate="mask_editor_no_fields">- keine Felder definiert -</div>'
        else:
            mapping_header = self.getMappingHeader()
            if mapping_header:
                ret += '<div class="label" i18n:translate="mask_edit_header">TEXT</div><div class="row">%s</div>' % (
                    esc(mapping_header))

        # check if all the orderpos attributes are the same which causes problems with sorting
        z = [t for t in self.children.order_by(Node.orderpos)]
        if all(z[0].orderpos == item.orderpos for item in z):
            k = 0
            for elem in z:
                elem.orderpos = elem.orderpos + k
                k += 1
            db.session.commit()

        i = 0
        fieldlist = {}  # !!!getAllMetaFields()
        for item in self.children.order_by(Node.orderpos):
            t = getMetadataType(item.get("type"))
            ret += t.getMetaHTML(self, i, language=language, fieldlist=fieldlist)  # get formated line specific of type (e.g. field)
            i += 1

        if len(self.children) > 0:
            mapping_footer = self.getMappingFooter()
            if mapping_footer:
                ret += '<div class="label" i18n:translate="mask_edit_footer">TEXT</div><div class="row">%s</div>' % (
                    esc(mapping_footer))
        ret += '</form>'
        return ret

    """ """

    def editItem(self, req):
        for key in req.params.keys():
            # edit field
            if key.startswith("edit_"):
                item = q(Node).get(req.params.get("edit", ""))
                t = getMetadataType(item.get("type"))
                ret = '<form method="post" name="myform">'
                ret += '<input value="' + _core_csrfform.get_token() + '" type="hidden" name="csrf_token">'
                return ret + '%s</form>' % (t.getMetaEditor(item, req))

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
            ret = '<form method="post" name="myform">'
            ret += '<input value="' + _core_csrfform.get_token() + '" type="hidden" name="csrf_token">'
            return ret + u'{}</form>'.format(t.getMetaEditor(item, req))

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
            ret += '<input value="' + _core_csrfform.get_token() + '" type="hidden" name="csrf_token">'
            ret += '<input type="hidden" name="pid" value="' + req.params.get("pid") + '"/>'
            ret += '<div class="label">&nbsp;</div><button type="submit" name="new_" style="width:100px" i18n:translate="mask_editor_ok"> OK </button>'
            ret += '&nbsp;&nbsp;<button type="submit" onclick="setCancel(document.myform.op)" i18n:translate="mask_editor_cancel">Abbrechen</button><br/>'
            ret += '</div></form>'
            return _tal.processTAL({}, string=ret, macro=None, request=req)

        if req.params.get("edit", " ") == " " and req.params.get("op", "") != "new":
            # create new node
            item = q(Node).get(req.params.get("id"))
            t = getMetadataType(req.params.get("type"))
            ret = '<form method="post" name="myform">'
            ret += '<input value="' + _core_csrfform.get_token() + '" type="hidden" name="csrf_token">'
            return ret + '%s</form>' % (t.getMetaEditor(item, req))


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
        return self.get("exportmapping").replace(";", " ").split()

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
                    logg.error("node id error for id '%s'", id)
        if ustr(pid) == "0":
            self.children.append(item)
        else:
            node = q(Node).get(pid)
            node.children.append(item)
        db.session.commit()
        return item

    ''' delete given  maskitem '''

    def deleteMaskitem(self, itemid):

        def delete_maskitems_recursive(item):
            if item.type != 'maskitem':
                return
            for child in item.children:
                delete_maskitems_recursive(child)
            db.session.delete(item)

        item = q(Node).get(itemid)

        assert item.type == 'maskitem'

        for parent in item.parents:
            i = 0
            for child in parent.children.order_by(Node.orderpos):
                if child.id == item.id:
                    continue
                child.orderpos = i
                i += 1

        delete_maskitems_recursive(item)


""" class for editor/view masks """


@check_type_arg
class Maskitem(Node):

    _metafield_rel = children_rel("Metafield", backref="maskitems", lazy="joined", viewonly=True)

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


_metatypes = {}


def _metatype_class(cls):
    name = cls.get_name4schema()
    logg.debug("loading metatype class %s", name)
    instance = cls()
    assert name not in _metatypes
    _metatypes[name] = instance
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
        for _, cls in inspect.getmembers(module, is_metatype_class):
            _metatype_class(cls)


def init():
    pkg_dirs = ["schema/mask", "metadata"]
    for pkg_dir in pkg_dirs:
        load_metatype_module(config.basedir, pkg_dir)


def getMetadataType(name):
    try:
        return _metatypes[name]
    except KeyError:
        raise LookupError("No such metatype: " + name)


def getMetaFieldTypeNames():
    return {
            name:"fieldtype_{}".format(name)
            for name,instance in _metatypes.iteritems()
            if "meta" in ustr(instance)
           }


def getMetaFieldTypes():
    ret = {name:getMetadataType(name) for name in _metatypes}
    return {name:type_ for name,type_ in _metatypes.iteritems() if type_.isFieldType()}

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

        with suppress(AttributeError, warn=False):
            if self.getSchema():
                l += getMetaType(self.getSchema()).getMetaFields(type)
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
