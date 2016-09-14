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
import sys

import logging

from web.admin.adminutils import Overview, getAdminStdVars, getSortCol, getFilter
from web.common.acl_web import makeList
from utils.utils import removeEmptyStrings, esc
from core.translation import lang, t
from schema.schema import getMetaFieldTypeNames, getMetaType, updateMetaType, existMetaType, deleteMetaType, fieldoption, moveMetaField, getMetaField, deleteMetaField, getFieldsForMeta, dateoption, requiredoption, existMetaField, updateMetaField, generateMask, cloneMask, exportMetaScheme, importMetaSchema
from schema.schema import VIEW_DEFAULT
from schema.bibtex import getAllBibTeXTypes
from schema import citeproc

from utils.fileutils import importFileToRealname
# metafield methods
from .metatype_field import showDetailList, FieldDetail
# meta mask methods
from .metatype_mask import showMaskList, MaskDetails

from contenttypes.data import Data

from core import Node
from core import db
from core.systemtypes import Metadatatypes
from schema.schema import Metadatatype, Mask
from core.database.postgres.permission import NodeToAccessRuleset

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


def validate(req, op):
    path = req.path[1:].split("/")

    if len(path) == 3 and path[2] == "overview":
        return showFieldOverview(req)

    if len(path) == 4 and path[3] == "editor":
        res = showEditor(req)
        return res

    if len(path) == 5 and path[3] == "editor" and path[4] == "show_testnodes":
        
        raise NotImplementedError("")

        template = req.params.get('template', '')
        testnodes_list = req.params.get('testnodes', '')
        width = req.params.get('width', '400')
        item_id = req.params.get('item_id', None)

        mdt_name = path[1]
        mask_name = path[2]

        mdt = q(Metadatatypes).one().children.filter_by(name=mdt_name).one()
        mask = mdt.children.filter_by(name=mask_name).one()

        sectionlist = []
        for nid in [x.strip() for x in testnodes_list.split(',') if x.strip()]:
            section_descr = {}
            section_descr['nid'] = nid
            section_descr['error_flag'] = ''  # in case of no error

            node = q(Node).get(nid)
            section_descr['node'] = node
            if node and node.has_data_access():
                try:
                    node_html = mask.getViewHTML([node], VIEW_DEFAULT, template_from_caller=[template, mdt, mask, item_id])
                    section_descr['node_html'] = node_html
                except:
                    logg.exception("exception while evaluating template")
                    error_text = str(sys.exc_info()[1])
                    template_line = 'for node id ' + ustr(nid) + ': ' + error_text
                    try:
                        m = re.match(r".*line (?P<line>\d*), column (?P<column>\d*)", error_text)
                        if m:
                            mdict = m.groupdict()
                            line = int(mdict.get('line', 0))
                            column = int(mdict.get('column', 0))
                            error_text = error_text.replace('line %d' % line, 'template line %d' % (line - 1))
                            template_line = 'for node id ' + ustr(nid) + '<br/>' + error_text + '<br/><code>' + esc(template.split(
                                "\n")[line - 2][0:column - 1]) + '<span style="color:red">' + esc(template.split("\n")[line - 2][column - 1:]) + '</span></code>'
                    except:
                        pass
                    section_descr['error_flag'] = 'Error while evaluating template:'
                    section_descr['node_html'] = template_line
            elif node and not node.has_data_access():
                section_descr['error_flag'] = 'no access'
                section_descr['node_html'] = ''
            if node is None:
                section_descr['node'] = None
                section_descr['error_flag'] = 'NoSuchNodeError'
                section_descr['node_html'] = 'for node id ' + ustr(nid)
            sectionlist.append(section_descr)

        # remark: error messages will be served untranslated in English
        # because messages from the python interpreter (in English) will be added

        return req.getTAL("web/admin/modules/metatype.html", {'sectionlist': sectionlist}, macro="view_testnodes")

    if len(path) == 2 and path[1] == "info":
        return showInfo(req)

    if "file" in req.params and hasattr(req.params["file"], "filesize") and req.params["file"].filesize > 0:
        # import scheme from xml-file
        importfile = req.params.get("file")
        if importfile.tempname != "":
            xmlimport(req, importfile.tempname)

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
                deleteMetaType(key[7:-2])
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
                return FieldDetail(req, req.params.get("parent"), "")

            # edit meta field
            elif key.startswith("editdetail_"):
                return FieldDetail(req, req.params.get("parent"), key[11:-2])

            # delete metafield: key[13:-2] = pid | n
            elif key.startswith("deletedetail_"):
                deleteMetaField(req.params.get("parent"), key[13:-2])
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

            if existMetaField(req.params.get("parent"), req.params.get("mname")) and req.params.get("form_op", "") == "save_newdetail":
                return FieldDetail(req, req.params.get("parent"), req.params.get("orig_name", ""), 3)  # field still existing
            elif req.params.get("mname", "") == "" or req.params.get("mlabel", "") == "":
                return FieldDetail(req, req.params.get("parent"), req.params.get("orig_name", ""), 1)
            elif not checkString(req.params.get("mname", "")):
                # if the name contains wrong characters
                return FieldDetail(req, req.params.get("parent"), req.params.get("orig_name", ""), 4)

            _option = ""
            for o in req.params.keys():
                if o.startswith("option_"):
                    _option += o[7]

            _fieldvalue = ""
            if req.params.get("mtype", "") + "_value" in req.params.keys():
                _fieldvalue = req.params.get(req.params.get("mtype") + "_value")

            _filenode = None
            if "valuesfile" in req.params.keys():
                valuesfile = req.params.pop("valuesfile")
                _filenode = importFileToRealname(valuesfile.filename, valuesfile.tempname)

            _attr_dict = {}
            if req.params.get("mtype", "") + "_handle_attrs" in req.params.keys():

                attr_names = [s.strip() for s in req.params.get(req.params.get("mtype", "") + "_handle_attrs").split(",")]
                key_prefix = req.params.get("mtype", "") + "_attr_"

                for attr_name in attr_names:
                    attr_value = req.params.get(key_prefix + attr_name, "")
                    _attr_dict[attr_name] = attr_value

            updateMetaField(req.params.get("parent", ""), req.params.get("mname", ""),
                            req.params.get("mlabel", ""), req.params.get("orderpos", ""),
                            req.params.get("mtype", ""), _option, req.params.get("mdescription", ""),
                            _fieldvalue, fieldid=req.params.get("fieldid", ""),
                            filenode=_filenode,
                            attr_dict=_attr_dict)

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
                mtype = getMetaType(req.params.get("parent"))
                mtype.children.remove(q(Node).get(key[11:-2]))
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
    mtypes = q(Metadatatypes).one().children.order_by("name").all()
    actfilter = getFilter(req)

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
    if order != "":
        if int(order[0:1]) == 0:
            mtypes.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))
        elif int(order[0:1]) == 1:
            mtypes.sort(lambda x, y: cmp(x.getLongName().lower(), y.getLongName().lower()))
        elif int(order[0:1]) == 2:
            mtypes.sort(lambda x, y: cmp(x.getDescription().lower(), y.getDescription().lower()))
        elif int(order[0:1]) == 3:
            mtypes.sort(lambda x, y: cmp(x.getActive(), y.getActive()))
        elif int(order[0:1]) == 4:
            mtypes.sort(lambda x, y: cmp(x.getDatatypeString().lower(), y.getDatatypeString().lower()))
        if int(order[1:]) == 1:
            mtypes.reverse()
    else:
        mtypes.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))

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
    v["get_classname_for_typestring"] = Node.get_classname_for_typestring
    v['dtypes'] = Node.__mapper__.polymorphic_map  # is used to prevent missing plugins from causing error
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["filterattrs"] = [("id", "admin_metatype_filter_id"), ("name", "admin_metatype_filter_name")]
    v["filterarg"] = req.params.get("filtertype", "id")
    return req.getTAL("web/admin/modules/metatype.html", v, macro="view_type")


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
    v["datatypes"].sort(lambda x, y: cmp(t(lang(req), x.__name__), t(lang(req), y.__name__)))
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
    return req.getTAL("web/admin/modules/metatype.html", v, macro="modify_type")


""" popup info form """


def showInfo(req):
    return req.getTAL("web/admin/modules/metatype.html", {"fieldtypes": getMetaFieldTypeNames()}, macro="show_info")

""" popup form with field definition """


def showFieldOverview(req):
    path = req.path[1:].split("/")
    fields = getFieldsForMeta(path[1])
    fields.sort(lambda x, y: cmp(x.orderpos, y.orderpos))

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
                # field of export mask
                item.set("attribute", req.params.get("attribute"))
                item.set("fieldtype", req.params.get("fieldtype"))
                mf = req.params.get("mappingfield").split(";")
                if req.params.get("fieldtype") == "mapping":  # mapping field of mapping definition selected
                    item.set("mappingfield", mf[0])
                else:  # attribute name as object name
                    item.set("mappingfield", ";".join(mf[1:]))
                db.session.commit()
            else:
                f = q(Node).get(long(req.params.get("field")))

            field = item.children
            try:
                field = list(field)[0]
                if ustr(field.id) != req.params.get("field"):
                    item.children.remove(field)
                    item.children.append(f)
                field.setValues(req.params.get(u"{}_value".format(field.get("type")), u""))
                db.session.commit()
            except:
                logg.exception("exception in showEditor / saveedit, ignore")
                pass

        elif req.params.get("op", "") == "new":
            if req.params.get("fieldtype", "") == "common" and req.params.get("field"):
                # existing field used
                fieldid = long(req.params.get("field"))
            elif "mappingfield" in req.params.keys():
                # new mapping field
                fieldid = ""  # long(req.params.get("mappingfield"))
                label = "mapping"

            else:
                # create new metaattribute
                parent = req.params.get("metadatatype").getName()
                fieldvalue = req.params.get(req.params.get("newfieldtype", "") + '_value', "")

                if req.params.get("type") == "label":
                    # new label
                    fieldid = ""
                else:
                    # normal field
                    updateMetaField(parent, req.params.get("fieldname"), label, 0,
                                    req.params.get("newfieldtype"), option="", description=req.params.get("description", ""),
                                    fieldvalues=fieldvalue, fieldvaluenum="", fieldid="")
                    fieldid = ustr(getMetaField(parent, req.params.get("fieldname")).id)

            item = editor.addMaskitem(label, req.params.get("type"), fieldid, req.params.get("pid", "0"))

            if "mappingfield" in req.params.keys():
                item.set("attribute", req.params.get("attribute"))
                item.set("fieldtype", req.params.get("fieldtype"))
                mf = req.params.get("mappingfield").split(";")
                if req.params.get("fieldtype") == "mapping":  # mapping field of mapping definition selected
                    item.set("mappingfield", mf[0])
                else:  # attribute name as object name
                    item.set("mappingfield", ";".join(mf[1:]))
                db.session.commit()

            position = req.params.get("insertposition", "end")
            if position == "end":
                # insert at the end of existing mask
                item.orderpos = len(q(Node).get(req.params.get("pid")).children) - 1
                db.session.commit()
            else:
                # insert at special position
                fields = editor.getMaskFields()
                fields.all().sort(lambda x, y: cmp(x.orderpos, y.orderpos))
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
        item.setTestNodes(req.params.get("testnodes", u""))
        item.setMultilang(req.params.get("multilang", u""))
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
            fields.sort(lambda x, y: cmp(x.orderpos, y.orderpos))
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
            v["editor"] = req.getTALstr(editor.getMetaMask(language=lang(req)), {})
        except:
            logg.exception("exception in showEditor")
            v["editor"] = editor.getMetaMask(language=lang(req))

    v["title"] = editor.name

    return req.getTAL("web/admin/modules/metatype.html", v, macro="editor_popup")


def changeOrder(parent, up, down):
    """ change order of given nodes """
    i = 0
    for child in parent.children.sort_by_orderpos():
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
            child.orderpos = pos
            db.session.commit()
            i = i + 1
        except:
            pass
