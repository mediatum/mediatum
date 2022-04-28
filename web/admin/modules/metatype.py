# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import operator as _operator
import re
import sys

import logging
import mediatumtal.tal as _tal
import sqlalchemy as _sqlalchemy

from web.admin.adminutils import Overview, getAdminStdVars, getSortCol, getFilter
from web.common.acl_web import makeList
from utils.utils import removeEmptyStrings, esc, suppress
from core.translation import lang, t
import core.translation as _translation
from schema.schema import getMetaFieldTypeNames, getMetaType, updateMetaType, existMetaType, deleteMetaType, fieldoption, moveMetaField, getMetaField, deleteMetaField, getFieldsForMeta, dateoption, requiredoption, existMetaField, updateMetaField, generateMask, cloneMask, exportMetaScheme, importMetaSchema
from schema.schema import VIEW_DEFAULT
from schema.bibtex import getAllBibTeXTypes
from schema import citeproc
import schema.schema as _schema

from utils.fileutils import importFile
# metafield methods
from .metatype_field import showDetailList, FieldDetail
# meta mask methods
from .metatype_mask import showMaskList, MaskDetails

from contenttypes.data import Data
import contenttypes as _contenttypes

from core import Node
from core import db
import core.nodecache as _nodecache
import core.systemtypes as _systemtypes
from schema.schema import Metadatatype, Mask
from core.database.postgres.permission import NodeToAccessRuleset
import core.database.postgres.node as _node

q = db.query

logg = logging.getLogger(__name__)


def getInformation():
    return {"version": "1.0"}

""" checks a string whether it only contains the alphanumeric chars as well as "-" "." """


def checkString(string):
    result = re.match("([\w\-\.]+)", string)
    if result is not None and result.group(0) == string:
        return True
    return False


def add_remove_rulesets_from_metadatatype(mtype, new_ruleset_names):
    new_ruleset_names = set(new_ruleset_names)
    current_ruleset_assocs_by_ruleset_name = {rs.ruleset.name: rs for rs in mtype.access_ruleset_assocs.filter_by(ruletype=u"read")}
    current_ruleset_names = set(current_ruleset_assocs_by_ruleset_name)
    removed_ruleset_names = current_ruleset_names - new_ruleset_names
    added_ruleset_names = new_ruleset_names - current_ruleset_names
    
    for ruleset_name in removed_ruleset_names:
        rsa = current_ruleset_assocs_by_ruleset_name[ruleset_name]
        mtype.access_ruleset_assocs.remove(rsa)
    
    for ruleset_name in added_ruleset_names:
        mtype.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=ruleset_name, ruletype=u"read"))


def _get_nodecount_per_metaschema():
    """
    evaluate the number of linked nodes per schema for all schemata's
    :return: dict with schema as key and number of linked nodes of this schema as value
    """

    root_id = _nodecache.get_root_node().id
    noderelation = _sqlalchemy.orm.aliased(_node.t_noderelation)
    return dict(q(Node.schema, _sqlalchemy.func.count(_sqlalchemy.func.distinct(Node.id)))
                .join(noderelation, noderelation.c.cid == Node.id)
                .filter(noderelation.c.nid == root_id)
                .group_by(Node.schema)
                )


def validate(req, op):
    path = req.mediatum_contextfree_path[1:].split("/")

    if len(path) == 3 and path[2] == "overview":
        return showFieldOverview(req)

    if len(path) == 4 and path[3] == "editor":
        res = showEditor(req)
        return res

    if len(path) == 2 and path[1] == "info":
        return showInfo(req)

    # import scheme from xml-file
    importfile = req.files.get("file")
    if importfile:
        importMetaSchema(importfile)

    if req.params.get("acttype", "schema") == "schema":
        # section for schema
        for key in req.params.keys():
            # create new metadatatype
            if key.startswith("new"):
                return MetatypeDetail(req, "")

            # edit metadatatype
            elif key.startswith("edit_"):
                return MetatypeDetail(req, key[5:-2])

            # delete metadata
            elif key.startswith("delete_"):
                schema_name = key[7:-2]
                if schema_name in _get_nodecount_per_metaschema():
                    raise RuntimeError(u"schema '{}' is used!".format(schema_name))
                deleteMetaType(schema_name)
                db.session.commit()
                break

            # show details for given metadatatype
            elif key.startswith("detaillist_"):
                return showDetailList(req, key[11:-2])

            # show masklist for given metadatatype
            elif key.startswith("masks_"):
                return showMaskList(req, key[6:-2])

        # save schema
        if "form_op" in req.params.keys():
            if req.params.get("form_op", "") == "cancel":
                return view(req)

            if req.params.get("mname", "") == "" or req.params.get("mlongname", "") == "" or req.params.get("mdatatypes", "") == "":
                return MetatypeDetail(req, req.params.get("mname_orig", ""), 1)  # no name was given
            elif not checkString(req.params.get("mname", "")):
                return MetatypeDetail(req, req.params.get("mname_orig", ""), 4)  # if the name contains wrong characters
            elif req.params.get("mname_orig", "") != req.params.get("mname", "") and existMetaType(req.params.get("mname")):
                return MetatypeDetail(req, req.params.get("mname_orig", ""), 2)  # metadata still existing

            _active = 0
            if req.params.get("mactive", "") != "":
                _active = 1
            updateMetaType(req.params.get("mname", ""),
                           description=req.params.get("description", ""),
                           longname=req.params.get("mlongname", ""), active=_active,
                           datatypes=req.params.get("mdatatypes", "").replace(";", ", "),
                           bibtexmapping=req.params.get("mbibtex", ""),
                           citeprocmapping=req.params.get("mciteproc", ""),
                           orig_name=req.params.get("mname_orig", ""))
            mtype = q(Metadatatype).filter_by(name=req.params.get("mname")).scalar()
            if mtype:
                new_ruleset_names = set(req.form.getlist("leftread"))
                add_remove_rulesets_from_metadatatype(mtype, new_ruleset_names)

            db.session.commit()

    elif req.params.get("acttype") == "field":
        # section for fields
        for key in req.params.keys():
            # create new meta field
            if key.startswith("newdetail_"):
                return FieldDetail(req, "")

            # edit meta field
            elif key.startswith("editdetail_"):
                return FieldDetail(req, key[11:-2])

            # delete metafield: key[13:-2] = pid | n
            elif key.startswith("deletedetail_"):
                deleteMetaField(req.params.get("parent"), key[13:-2])
                db.session.commit()
                return showDetailList(req, req.params.get("parent"))

            # change field order up
            if key.startswith("updetail_"):
                moveMetaField(req.params.get("parent"), key[9:-2], -1)
                return showDetailList(req, req.params.get("parent"))

            # change field order down
            elif key.startswith("downdetail_"):
                moveMetaField(req.params.get("parent"), key[11:-2], 1)
                return showDetailList(req, req.params.get("parent"))

        if "form_op" in req.params.keys():
            if req.params.get("form_op", "") == "cancel":
                return showDetailList(req, req.params.get("parent"))

            if existMetaField(req.params.get("parent"), req.params.get("mname")) and \
                    (req.params.get("form_op", "")  == "save_newdetail" or req.params.get("mname") != req.params.get("mname_orig")):
                return FieldDetail(req, error="admin_duplicate_error")
            elif req.params.get("mname", "") == "" or req.params.get("mlabel", "") == "":
                return FieldDetail(req, error="admin_mandatory_error")
            elif not checkString(req.params.get("mname", "")):
                return FieldDetail(req, error="admin_metafield_error_badchars")

            fieldvalue = "{}_value".format(req.params.get("mtype", ""))
            if fieldvalue in req.params:
                fieldvalue = req.params.get(fieldvalue)
            else:
                fieldvalue = ""

            updateMetaField(
                    req.values["parent"],
                    req.values["mname"],
                    req.values.get("mlabel", ""),
                    req.values["mtype"],
                    tuple(o[7] for o in req.params if o.startswith("option_")),
                    req.values.get("mdescription", ""),
                    fieldvalue,
                    req.values.get("fieldid", ""),
                   )

        return showDetailList(req, req.params.get("parent"))

    elif req.params.get("acttype") == "mask":

        # section for masks
        for key in req.params.keys():

            # new mask
            if key.startswith("newmask_"):
                return MaskDetails(req, req.params.get("parent"), "")

            # edit metatype masks
            elif key.startswith("editmask_"):
                return MaskDetails(req, req.params.get("parent"), key[9:-2], err=0)

            # delete mask
            elif key.startswith("deletemask_"):
                _schema.delete_mask(q(Node).get(key[11:-2]))
                db.session.commit()
                return showMaskList(req, req.params.get("parent"))

            # create autmatic mask with all fields
            elif key.startswith("automask_"):
                generateMask(getMetaType(req.params.get("parent")))
                return showMaskList(req, req.params.get("parent"))

            # cope selected mask
            if key.startswith("copymask_"):
                k = key[9:-2]
                if k.isdigit():
                    mask = q(Mask).get(k)
                else:
                    mtype = getMetaType(req.params.get("parent"))
                    mask = mtype.getMask(k)
                cloneMask(mask, u"copy_" + mask.name)
                return showMaskList(req, req.params.get("parent"))

        if "form_op" in req.params.keys():
            if req.params.get("form_op", "") == "cancel":
                return showMaskList(req, req.params.get("parent"))

            if req.params.get("mname", "") == "":
                return MaskDetails(req, req.params.get("parent", ""), req.params.get("morig_name", ""), err=1)
            elif not checkString(req.params.get("mname", "")):
                # if the name contains wrong characters
                return MaskDetails(req, req.params.get("parent", ""), req.params.get("morig_name", ""), err=4)

            mtype = q(Metadatatype).filter_by(name=q(Node).get(req.params.get("parent", "")).name).one()
            if req.params.get("form_op") == "save_editmask":
                mask = mtype.get_mask(req.params.get("mname", ""))
                # in case of renaming a mask the mask cannot be detected via the new mname
                # then detect mask via maskid
                if not mask:
                    mtype = getMetaType(req.params.get("parent"))
                    mask = mtype.children.filter_by(id =req.params.get("maskid", "")).scalar()

            elif req.params.get("form_op") == "save_newmask":
                mask = Mask(req.params.get("mname", ""))
                mtype.children.append(mask)
                db.session.commit()
            mask.name = req.params.get("mname")
            mask.setDescription(req.params.get("mdescription"))
            mask.setMasktype(req.params.get("mtype"))
            mask.setSeparator(req.params.get("mseparator"))
            db.session.commit()

            if req.params.get("mtype") == "export":
                mask.setExportMapping(req.params.get("exportmapping") or "")
                mask.setExportHeader(req.params.get("exportheader"))
                mask.setExportFooter(req.params.get("exportfooter"))
                _opt = ""
                if "types" in req.params.keys():
                    _opt += "t"
                if "notlast" in req.params.keys():
                    _opt += "l"
                mask.setExportOptions(_opt)
                db.session.commit()

            mask.setLanguage(req.params.get("mlanguage", ""))
            mask.setDefaultMask("mdefault" in req.params.keys())

            for r in mask.access_ruleset_assocs.filter_by(ruletype=u'read'):
                db.session.delete(r)

            for key in req.params.keys():
                if key.startswith("left"):
                    for r in req.params.get(key).split(';'):
                        mask.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[4:]))
                    break
            db.session.commit()
        return showMaskList(req, ustr(req.params.get("parent", "")))
    return view(req)


""" show all defined metadatatypes """

def view(req):
    mtypes = _nodecache.get_metadatatypes_node().children.order_by("name").all()
    if set(q(Metadatatype).all()) - set(mtypes):
        raise RuntimeError(u"unlinked metadatatypes found")
    actfilter = getFilter(req)
    used_by = _get_nodecount_per_metaschema()

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", t(lang(req), "admin_filter_all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            if req.params.get("filtertype", "") == "id":
                mtypes = filter(lambda x: num.match(x.name), mtypes)
            else:
                mtypes = filter(lambda x: num.match(x.getLongName()), mtypes)
        elif actfilter == "else" or actfilter == t(lang(req), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9]|\.)')
            if req.params.get("filtertype", "") == "id":
                mtypes = filter(lambda x: not all.match(x.name), mtypes)
            else:
                mtypes = filter(lambda x: not all.match(x.getLongName()), mtypes)
        else:
            if req.params.get("filtertype", "") == "id":
                mtypes = filter(lambda x: x.name.lower().startswith(actfilter), mtypes)
            else:
                mtypes = filter(lambda x: x.getLongName().lower().startswith(actfilter), mtypes)

    pages = Overview(req, mtypes)
    order = getSortCol(req)

    # sorting
    if order:
        mtypes.sort(reverse=int(order[1:])==1, key={
            0:lambda mt:mt.name.lower(),
            1:lambda mt:mt.getLongName().lower(),
            2:lambda mt:mt.getDescription().lower(),
            3:_operator.methodcaller("getActive"),
            4:lambda mt:mt.getDatatypeString().lower(),
           }[int(order[:1])])
    else:
        mtypes.sort(key=lambda mt:mt.name.lower())

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader(
        [
            t(
                lang(req), "admin_meta_col_1"), t(
                lang(req), "admin_meta_col_2"), t(
                    lang(req), "admin_meta_col_3"), t(
                        lang(req), "admin_meta_col_4"), t(
                            lang(req), "admin_meta_col_5"), t(
                                lang(req), "admin_meta_col_6")])
    v["metadatatypes"] = mtypes
    v["used_by"] = used_by
    v["get_classname_for_typestring"] = Node.get_classname_for_typestring
    v['dtypes'] = Node.__mapper__.polymorphic_map  # is used to prevent missing plugins from causing error
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["filterattrs"] = [("id", "admin_metatype_filter_id"), ("name", "admin_metatype_filter_name")]
    v["filterarg"] = req.params.get("filtertype", "id")
    v["csrf"] = req.csrf_token.current_token
    v["translate"] = _translation.translate
    v["language"] = lang(req)
    return _tal.processTAL(v, file="web/admin/modules/metatype.html", macro="view_type", request=req)


""" form for metadata (edit/new) """


def MetatypeDetail(req, id, err=0):
    v = getAdminStdVars(req)

    if err == 0 and id == "":
        # new metadatatype
        metadatatype = Metadatatype(u"")
        db.session.commit()
        v["original_name"] = ""

    elif id != "" and err == 0:
        # edit metadatatype
        metadatatype = getMetaType(id)
        v["original_name"] = metadatatype.getName()

    else:
        # error
        metadatatype = Metadatatype(req.params["mname"])
        metadatatype.set("description", req.params["description"])
        metadatatype.set("longname", req.params["mlongname"])
        metadatatype.set("active", "mactive" in req.params)
        metadatatype.set("datatypes", req.params.get("mdatatypes", "").replace(";", ", "))
        metadatatype.set("bibtexmapping", req.params.get("mbibtex", ""))
        metadatatype.set("citeprocmapping", req.params.get("mciteproc", ""))
        db.session.commit()
        v["original_name"] = req.params["mname_orig"]
    d = Data()
    v["datatypes"] = d.get_all_datatypes()
    v["datatypes"].sort(key=lambda dt:t(lang(req), dt.__name__))
    v["metadatatype"] = metadatatype
    v["error"] = err
    v["bibtextypes"] = getAllBibTeXTypes()
    v["bibtexselected"] = metadatatype.get("bibtexmapping").split(";")
    v["citeproctypes"] = citeproc.TYPES
    v["citeprocselected"] = metadatatype.get("citeprocmapping").split(";")

    try:
        rules = [r.ruleset_name for r in metadatatype.access_ruleset_assocs.filter_by(ruletype=u'read')]
    except:
        rules = []

    v["acl"] = makeList(req, "read", removeEmptyStrings(rules), {}, overload=0, type="read")
    v["filtertype"] = req.params.get("filtertype", "")
    v["actpage"] = req.params.get("actpage")
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/metatype.html", macro="modify_type", request=req)


""" popup info form """


def showInfo(req):
    return _tal.processTAL({"fieldtypes": getMetaFieldTypeNames(), "csrf": req.csrf_token.current_token}, file="web/admin/modules/metatype.html", macro="show_info", request=req)

""" popup form with field definition """


def showFieldOverview(req):
    path = req.mediatum_contextfree_path[1:].split("/")
    fields = getFieldsForMeta(path[1])
    fields.sort(key=_operator.attrgetter("orderpos"))

    v = {}
    v["metadatatype"] = getMetaType(path[1])
    v["metafields"] = fields
    v["fieldoptions"] = fieldoption
    v["fieldtypes"] = getMetaFieldTypeNames()
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/metatype.html", macro="show_fieldoverview", request=req)

""" export metadatatype-definition (XML) """


def export(req, name):
    return exportMetaScheme(name)

""" import definition from file """


def xmlimport(req, filename):
    importMetaSchema(filename)


def _set_export_maskitem_fields(maskitem, has_exportmapping, mappingfield, fieldtype, attribute):
    """
    sets the maskitem attributes of an exportmask
    :param maskitem:
    :param has_exportmapping
    :param mappingfield: mappingfield as list
    :param fieldtype: 'mapping' or 'attribute
    :param attribute:
    :return:

    """
    if not has_exportmapping:
        mappingfield = "".join(mappingfield);
    elif fieldtype == "mapping":  # mapping field of mapping definition selected
        mappingfield = mappingfield[0]
    else:  # attribute name as object name
        mappingfield = ";".join(mappingfield[1:])
    maskitem.set("mappingfield", (mappingfield))
    maskitem.set("fieldtype", fieldtype)
    maskitem.set("attribute", attribute)
    db.session.commit()


def showEditor(req):
    path = req.mediatum_contextfree_path[1:].split("/")
    mtype = getMetaType(path[1])
    editor = mtype.getMask(path[2])

    req.params["metadatatype"] = mtype
    for key in req.params.keys():
        if req.params.get("op", "") == "cancel":
            if "savedetail" in req.params.keys():
                del req.params["savedetail"]
            break

        if key.startswith("up_"):
            changeOrder(q(Node).get(key[3:-2]).parents[0], q(Node).get(key[3:-2]).orderpos, -1)
            break

        if key.startswith("down_"):
            changeOrder(q(Node).get(key[5:-2]).parents[0], -1, q(Node).get(key[5:-2]).orderpos)
            break

        if key.startswith("delete_"):
            editor.deleteMaskitem(key[7:-2])
            db.session.commit()
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
            if req.params.get("type")in("vgroup", "hgroup"):
                req.params["type"] = "field"
                req.params["op"] = "new"
            if "savedetail" in req.params.keys():
                del req.params["savedetail"]
            break

    if req.params.get("op", "") == "group":
        # create new group for selected objects
        req.params["op"] = "new"
        req.params["edit"] = " "
        req.params["type"] = req.params.get("group_type")
        req.params["pid"] = q(Node).get(req.params.get("sel_id").split(";")[0]).parents[0].id

    if "saveedit" in req.params.keys() and req.params.get("op", "") != "cancel":
        # update node
        label = req.params.get("label", "-new-")
        if req.params.get("op", "") == "edit":
            item = q(Node).get(req.params.get("id"))
            item.setLabel(req.params.get("label", ""))
            db.session.commit()
            if "mappingfield" in req.params.keys():
                _set_export_maskitem_fields(
                    item,
                    editor.get("exportmapping"),
                    req.values.getlist("mappingfield"),
                    req.values["fieldtype"],
                    req.values["attribute"]
                )

        elif req.params.get("op", "") == "new":
            if "mappingfield" in req.params:
                # new mapping field
                fieldid = ""  # long(req.params.get("mappingfield"))
                label = "mapping"

            elif req.params.get("field"):
                # existing field used
                fieldid = long(req.params.get("field"))

            item = editor.addMaskitem(label, req.params.get("type"), fieldid, req.params.get("pid", "0"))

            if "mappingfield" in req.params.keys():
                _set_export_maskitem_fields(
                    item,
                    editor.get("exportmapping"),
                    req.values.getlist("mappingfield"),
                    req.values["fieldtype"],
                    req.values["attribute"]
                )
            position = req.params.get("insertposition", "end")
            if position == "end":
                # insert at the end of existing mask
                item.orderpos = len(q(Node).get(req.params.get("pid")).children) - 1
                db.session.commit()
            else:
                # insert at special position
                fields = editor.getMaskFields()
                fields.all().sort(key=_operator.attrgetter("orderpos"))
                for f in fields:
                    if f.orderpos >= q(Node).get(position).orderpos and f.id != item.id:
                        f.orderpos = f.orderpos + 1
                item.orderpos = q(Node).get(position).orderpos - 1
                db.session.commit()

        item.setWidth(req.params.get("width", u'400'))
        item.setUnit(req.params.get("unit", u""))
        item.setDefault(req.params.get("default", u""))
        item.setFormat(req.params.get("format", u""))
        item.setSeparator(req.params.get("separator", u""))
        item.setDescription(req.params.get("description", u""))
        db.session.commit()

        if "required" in req.params.keys():
            item.setRequired(unicode(1))
        else:
            item.setRequired(unicode(0))
        db.session.commit()

    if "savedetail" in req.params.keys():
        label = req.params.get("label", "-new-")
        # save details (used for hgroup)
        if req.params.get("op", "") == "edit":
            item = q(Node).get(req.params.get("id"))
            item.setLabel(req.params.get("label", ""))
        elif req.params.get("op", "") == "new":
            if req.params.get("sel_id", "") != "":
                item = editor.addMaskitem(label, req.params.get("type"), req.params.get(
                    "sel_id", "")[:-1], long(req.params.get("pid", "0")))
            else:
                item = editor.addMaskitem(label, req.params.get("type"), 0, long(req.params.get("pid", "0")))
        db.session.commit()

        # move selected elementd to new item-container
        if req.params.get("sel_id", "") != "":
            pos = 0
            for i in req.params.get("sel_id")[:-1].split(";"):
                n = q(Node).get(i)  # node to move
                n.setOrderPos(pos)
                p = q(Node).get(n.parents()[0].id)  # parentnode
                p.children.remove(n)
                item.children.append(n)  # new group
                pos += 1
            db.session.commit()

        # position:
        position = req.params.get("insertposition", "end")
        if position == "end":
            # insert at the end of existing mask
            item.setOrderPos(len(q(Node).get(req.params.get("pid")).children) - 1)
            db.session.commit()
        else:
            # insert at special position
            fields = []
            pidnode = q(Node).get(req.params.get("pid"))
            for field in pidnode.getChildren():
                if field.getType().getName() == "maskitem" and field.id != pidnode.id:
                    fields.append(field)
            fields.sort(key=_operator.attrgetter("orderpos"))
            for f in fields:
                if f.orderpos >= q(Node).get(position).orderpos and f.id != item.id:
                    f.orderpos = f.orderpos + 1
            item.orderpos = q(Node).get(position).orderpos - 1
            db.session.commit()

        if "edit" not in req.params.keys():
            item.set("type", req.params.get("type", u""))
        item.setWidth(req.params.get("width", u'400'))
        item.setUnit(req.params.get("unit", u""))
        item.setDefault(req.params.get("default", u""))
        item.setFormat(req.params.get("format", u""))
        item.setSeparator(req.params.get("separator", u""))
        item.setDescription(req.params.get("description", u""))
        if "required" in req.params.keys():
            item.setRequired(unicode(1))
        else:
            item.setRequired(unicode(0))
        db.session.commit()

    v = {}
    v["edit"] = req.params.get("edit", "")
    if req.params.get("edit", "") != "":
        v["editor"] = editor.editItem(req)
    else:
        # show metaEditor
        v["editor"] = ""
        try:
            v["editor"] = _tal.processTAL({}, string=editor.getMetaMask(language=lang(req)), macro=None, request=req)
        except:
            logg.exception("exception in showEditor")
            v["editor"] = editor.getMetaMask(req)

    v["title"] = editor.name
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/metatype.html", macro="editor_popup", request=req)


def changeOrder(parent, up, down):
    """ change order of given nodes """
    i = 0
    for child in parent.children.sort_by_orderpos():
        with suppress(Exception, warn=False):
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
            child.orderpos = pos
            db.session.commit()
            i = i + 1
