# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging as _logging

import mediatumtal.tal as _tal

import core.translation as _core_translation
from schema.schema import getMetadataType, getAllMetaFields, VIEW_DATA_ONLY, Maskitem
from core import db
from core.metatype import Metatype
from core.database.postgres.node import Node
from utils.utils import suppress


_logg = _logging.getLogger(__name__)
q = db.query


class m_vgroup(Metatype):

    name = "vgroup"

    def getFormHTML(self, field, nodes, req):
        children_html = []
        for item in field.getChildren().sort_by_orderpos():
            if item.get("type") in ("hgroup", "vgroup", "field", "label"):
                f = getMetadataType(item.get("type"))
                children_html.append(f.getFormHTML(item, nodes, req))
            else:
                _logg.error("wrong field")
        v = dict(
                children_html="".join(children_html),
                label=field.getLabel(),
               )
        return _tal.processTAL(v, file="schema/mask/vgroup.html", macro="get_form_html", request=req)

    def getViewHTML(self, field, nodes, flags, language=None, template_from_caller=None, mask=None, use_label=True):
        if flags & VIEW_DATA_ONLY:
            ret = []
            for item in field.getChildren().sort_by_orderpos():
                f = getMetadataType(item.get("type"))
                ret.append(f.getViewHTML(item, nodes, flags, language=language))
            return ret
        else:
            # standard view

            ret = '<div class="mask_row"><fieldset>\n'
            if use_label:
                ret += '<legend>' + field.getLabel() + '</legend>'
            for item in field.getChildren().sort_by_orderpos():
                f = getMetadataType(item.get("type"))
                ret += '<div class="mask_row">' + f.getViewHTML(item, nodes, flags) + '</div>\n'
            ret += '</fieldset></div>\n'

        return ret

    def getMetaHTML(self, parent, index, sub=False, language=None, fieldlist={}, req=None):
        item = parent.children.order_by(Node.orderpos)[index]

        html_form = u"".join(getMetadataType(field.get("type")).getMetaHTML(
            item,
            idx,
            True,
            language=language,
            fieldlist=fieldlist,
        ) for idx, field in enumerate(item.children.order_by(Node.orderpos)))

        return _tal.processTAL(
            dict(
                html_form=html_form,
                item_id=item.id,
                item_type=item.get("type"),
                is_sub=sub,
                label=item.getLabel(),
                is_first=index==0,
                is_last=index==len(parent.getChildren())-1,
            ),
            file="schema/mask/vgroup.html",
            macro="admin_get_field_for_maskedit",
        )

    def getMetaEditor(self, item, req):
        """ editor mask for vgroup-field definition """
        fieldlist = getAllMetaFields()
        if len(item.getParents()) == 0:
            pid = req.params.get("pid", "")
        else:
            pid = item.getParents()[0].id

        if req.params.get("edit") == "None":
            item = Maskitem(name="", type="maskitem")
            item.set("type", "vgroup")

        details = ""
        i = 0
        for field in item.getChildren().sort_by_orderpos():
            f = getMetadataType(field.get("type"))
            details += f.getMetaHTML(
                    item,
                    i,
                    False,
                    fieldlist=fieldlist,
                    language=_core_translation.set_language(req.accept_languages),
                )
            i += 1

        if req.params.get("sel_id", "") != "":
            i = 0
            for id in req.params.get("sel_id")[:-1].split(";"):
                f = getMetadataType(q(Node).get(id).get("type"))
                with suppress(TypeError, warn=False):
                    details += f.getMetaHTML(item, i, False, itemlist=req.params.get("sel_id")
                                             [:-1].split(";"), ptype="vgroup", fieldlist=fieldlist)
                i += 1
        fields = []
        metadatatype = req.params.get("metadatatype")

        if req.params.get("op", "") == "new":
            pidnode = q(Node).get(req.params.get("pid"))
            if pidnode.get("type") in ("vgroup", "hgroup"):
                for field in pidnode.all_children:
                    if field.getType().getName() == "maskitem" and field.id != pidnode.id:
                        fields.append(field)
            else:
                for m in metadatatype.getMasks():
                    if ustr(m.id) == ustr(req.params.get("pid")):
                        for field in m.getChildren():
                            fields.append(field)
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))

        v = {}
        v["pid"] = pid
        v["item"] = item
        v["op"] = req.params.get("op", "")
        v["details"] = details
        v["fields"] = fields
        v["selid"] = req.params.get("sel_id", "")
        return _tal.processTAL(v, file="schema/mask/vgroup.html", macro="metaeditor", request=req)
