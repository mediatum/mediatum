# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import itertools as _itertools
import collections as _collections
import re

import sqlalchemy as _sqlalchemy

import mediatumtal.tal as _tal

from schema.mapping import getMapping, getMappingTypes, updateMapping, deleteMapping, updateMappingField, deleteMappingField, exportMapping, importMapping
from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
import core.translation as _translation

from core import Node
from core import db
import core.nodecache as _nodecache
from schema.mapping import Mapping, MappingField
import core.csrfform as _core_csrfform
import core.database.postgres.node as _node
import core.systemtypes as _core_systemtypes

q = db.query


_MaskitemsDependency = _collections.namedtuple(
    "_MaskitemsDependency",
    "metadatatypes_id mappingfield schema_name mask_name metafield_name"
)


def _get_maskitems_dependencies():
    """
    collect a list of all maskitems of all importmasks together with metadatatype and mask to which the maskitem belongs
     and the metafield specified in the attribute 'attribute' of the maskitem.
    :return: list of _MaskitemsDependency
    """
    metadatatype, mask, maskitem, metafield = (
        _sqlalchemy.orm.aliased(_node.Node) for _ in xrange(4))

    query = q(
        _core_systemtypes.Metadatatypes.id,
        maskitem.attrs['mappingfield'].astext,
        metadatatype.name,
        mask.name,
        metafield.name,
    )

    joins = (
        _core_systemtypes.Metadatatypes,
        metadatatype,
        mask,
        maskitem,
    )

    for parent, child in zip(joins[:-1], joins[1:]):
        nodemapping = _sqlalchemy.orm.aliased(_node.t_nodemapping)
        query = query.join(nodemapping, nodemapping.c.nid == parent.id)
        query = query.join(child, child.id == nodemapping.c.cid)
    query = query.join(metafield, metafield.id == maskitem.attrs['attribute'].astext.cast(_sqlalchemy.Integer))
    query = query.filter(mask.attrs['masktype'].astext == 'export')
    query = query.filter(maskitem.attrs['fieldtype'].astext == 'mapping')
    return tuple(_itertools.starmap(_MaskitemsDependency, query.all()))


def getInformation():
    return{"version": "1.0"}


def validate(req, op):
    if req.params.get("acttype", "mapping") == "mapping":

        if req.params.get("formtype", "") == "configuration" and "save_config" in req.params:
            mappingroot = _nodecache.get_mappings_node()
            mappingroot.set("mappingtypes", req.params.get("mappingtypes", "").replace("\r\n", ";").replace("\n", ";"))
            db.session.commit()
            return view(req)

        # import mapping from xml-file
        importfile = req.files.get("file")
        if importfile:
            importMapping(importfile)
        #  section for mapping
        for key in req.params.keys():
            if key.startswith("fieldlist_"):
                # list all defined fields
                return viewlist(req, key[10:-2])

            elif key.startswith("new"):
                # create new mapping
                return editMapping_mask(req, "")

            elif key.startswith("edit_"):
                # edit/create mapping
                return editMapping_mask(req, key[key.index("_") + 1:-2])

            elif key.startswith("delete_"):
                # delete mapping
                deleteMapping(key[7:-2])
                break

        if "form_op" in req.params.keys():
            if req.params.get("form_op", "") == "cancel":
                return view(req)
            # save mapping values
            if req.params.get("name", "") == "":
                return editMapping_mask(req, req.params.get("id", ""), 1)  # empty required field
            else:
                updateMapping(
                    req.params.get("name"),
                    namespace=req.params.get("namespace"),
                    namespaceurl=req.params.get("namespaceurl"),
                    description=req.params.get("description"),
                    header=req.params.get("header"),
                    footer=req.params.get("footer"),
                    separator=req.params.get("separator"),
                    standardformat=req.params.get("standardformat"),
                    id=req.params.get("id"),
                    mappingtype=req.params.get("mappingtype"),
                    active=req.params.get("active"))

    else:
        # section for mapping fields
        for key in req.params.keys():

            if key.startswith("newfield_"):
                # create new mapping field
                return editMappingField_mask(req, u"", q(Node).get(key[9:-2]))

            elif key.startswith("editfield_"):
                # create new mapping field
                return editMappingField_mask(req, key[10:-2], q(Node).get(req.params.get("parent")))

            elif key.startswith("deletefield_"):
                # delete mapping field
                deleteMappingField(key[12:-2])
                break

        if "form_op" in req.params.keys():
            if req.params.get("form_op", "") == "cancel":
                return viewlist(req, req.params.get("parent"))
            # save mapping field values
            if ustr(req.params["name"]) == "":
                # empty required field
                return editMappingField_mask(req, req.params.get("id", ""), q(Node).get(req.params.get("parent")), 1)
            else:
                _mandatory = False
                if "mandatory" in req.params.keys():
                    _mandatory = True
                updateMappingField(
                    req.params.get("parent"),
                    req.params.get("name"),
                    description=req.params.get("description"),
                    exportformat=req.params.get("exportformat"),
                    mandatory=_mandatory,
                    default=req.params.get("default"),
                    id=req.params.get("id"))
        return viewlist(req, req.params.get("parent"))

    return view(req)


def view(req):
    mappings = list(_nodecache.get_mappings_node().children)
    order = getSortCol(req)
    actfilter = getFilter(req)

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", _translation.t(_translation.set_language(req.accept_languages), "admin_filter_all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            mappings = filter(lambda x: num.match(x.name), mappings)

        elif actfilter == "else" or actfilter == _translation.t(_translation.set_language(req.accept_languages), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            mappings = filter(lambda x: not all.match(x.name), mappings)

        else:
            mappings = filter(lambda x: x.name.lower().startswith(actfilter), mappings)

    pages = Overview(req, mappings)

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            mappings.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))
        elif int(order[0:1]) == 1:
            mappings.sort(lambda x, y: cmp(x.getNamespace().lower(), y.getNamespace().lower()))
        elif int(order[0:1]) == 2:
            mappings.sort(lambda x, y: cmp(x.getNamespaceUrl().lower(), y.getNamespaceUrl().lower()))
        elif int(order[0:1]) == 3:
            mappings.sort(lambda x, y: cmp(x.getDescription().lower(), y.getDescription().lower()))
        elif int(order[0:1]) == 4:
            mappings.sort(lambda x, y: cmp(len(x.getFields()), len(y.getFields())))
        elif int(order[0:1]) == 5:
            mappings.sort(lambda x, y: cmp(x.getMappingType(), y.getMappingType()))
        elif int(order[0:1]) == 6:
            mappings.sort(lambda x, y: cmp(x.getActive(), y.getActive()))

        if int(order[1:]) == 1:
            mappings.reverse()
    else:
        mappings.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader(tuple(
        _translation.t(
             _translation.set_language(req.accept_languages),
            "admin_mapping_col_{}".format(col),
            )
        for col in xrange(1, 8)
        ))
    v["mappings"] = mappings
    v["options"] = []
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["mappingtypes"] = "\n".join(getMappingTypes())
    v["csrf"] = _core_csrfform.get_token()
    return _tal.processTAL(v, file="web/admin/modules/mapping.html", macro="view", request=req)


def editMapping_mask(req, id, err=0):
    if err == 0 and id == "":
        # new mapping
        mapping = Mapping(u"")
        db.session.commit()
    elif id != "":
        # edit mapping
        mapping = getMapping(id)
    else:
        # error while filling values
        mapping = Mapping(u"")
        mapping.name = req.params.get("name", u"")
        mapping.setDescription(req.params.get("description", u""))
        mapping.setNamespace(req.params.get("namespace", u""))
        mapping.setNamespaceUrl(req.params.get("namespaceurl", u""))
        mapping.setHeader(req.params.get("header"))
        mapping.setFooter(req.params.get("footer"))
        mapping.setSeparator(req.params.get("separator"))
        mapping.setStandardFormat(req.params.get("standardformat"))
        db.session.commit()

    v = getAdminStdVars(req)
    v["error"] = err
    v["mapping"] = mapping
    v["id"] = id
    v["actpage"] = req.params.get("actpage")
    v["mappingtypes"] = getMappingTypes()
    v["csrf"] = _core_csrfform.get_token()
    return _tal.processTAL(v, file="web/admin/modules/mapping.html", macro="modify", request=req)


def viewlist(req, id):
    mapping = getMapping(id)

    fields = list(mapping.getFields())
    order = getSortCol(req)
    actfilter = getFilter(req)

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", (_translation.set_language(req.accept_languages), "admin_filter_all")):
            None  # all mappings
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            fields = filter(lambda x: num.match(x.name), fields)

        elif actfilter == "else" or actfilter == _translation.t(_translation.set_language(req.accept_languages), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            fields = filter(lambda x: not all.match(x.name), fields)

        else:
            fields = filter(lambda x: x.name.lower().startswith(actfilter), fields)

    pages = Overview(req, fields)

    # sorting
    if order != "":
        if int(order[0:1]) == 0:
            fields.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))
        elif int(order[0:1]) == 1:
            fields.sort(lambda x, y: cmp(x.getDescription().lower(), y.getDescription().lower()))
        elif int(order[0:1]) == 2:
            fields.sort(lambda x, y: cmp(x.getMandatory(), y.getMandatory()))

        if int(order[1:]) == 1:
            fields.reverse()
    else:
        fields.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))

    maskitems_dependencies = _get_maskitems_dependencies()
    used_by = {field.id: "\n".join(['']+["{schema_name}: {mask_name}: {metafield_name}".format(**md._asdict())
                                         for md in maskitems_dependencies if md.mappingfield == str(field.id)])
               for field in fields}

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader(tuple(
        _translation.t(
            _translation.set_language(req.accept_languages),
            "admin_mappingfield_col_{}".format(col),
            )
        for col in xrange(1, 4)
        ), addparams=u"&detailof={}".format(unicode(mapping.id)))
    v["fields"] = fields
    v["used_by"] = used_by
    v["mapping"] = mapping
    v["options"] = []
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["csrf"] = _core_csrfform.get_token()
    v["translate"] = _translation.translate
    v["language"] = _translation.set_language(req.accept_languages)
    return _tal.processTAL(v, file="web/admin/modules/mapping.html", macro="viewlist", request=req)


def editMappingField_mask(req, id, parent, err=0):
    if err == 0 and id == "":
        # new mapping field
        field = MappingField(u"")
        db.session.add(field)
    elif id != "":
        # edit mapping field
        field = q(Node).get(id)
    else:
        # error while filling values
        field = MappingField(u"")
        field.name = req.params.get("name", u"")
        field.setDescription(req.params.get("description", u""))
        field.setExportFormat(req.params.get("exportformat", u""))
        if "mandatory" in req.params.keys():
            field.setMandatory("True")
        db.session.commit()

    v = getAdminStdVars(req)
    v["error"] = err
    v["field"] = field
    v["parent"] = parent
    v["actpage"] = req.params.get("actpage")
    v["csrf"] = _core_csrfform.get_token()
    return _tal.processTAL(v, file="web/admin/modules/mapping.html", macro="modifyfield", request=req)


""" export mapping-definition (XML) """


def export(req, name):
    return exportMapping(name)

""" import definition from file """


def xmlimport(req, filename):
    importMapping(filename)
