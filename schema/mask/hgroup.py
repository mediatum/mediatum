# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import itertools as _itertools

import mediatumtal.tal as _tal

import core.translation as _core_translation
from schema.schema import getMetadataType, getAllMetaFields, VIEW_DATA_ONLY, VIEW_SUB_ELEMENT, Maskitem

from core import db
from core.database.postgres.node import Node
from core.metatype import Metatype
from utils import utils as _utils_utils

q = db.query


class m_hgroup(Metatype):

    name = "hgroup"

    def getFormHTML(self, field, nodes, req):

        children_html = []
        for item in field.getChildren().sort_by_orderpos():
            f = getMetadataType(item.get("type"))
            children_html.append(f.getFormHTML(item, nodes, req))
        v = dict(
                children_html="".join(children_html),
                label=field.getLabel(),
               )
        return _tal.processTAL(v, file="schema/mask/hgroup.html", macro="get_form_html", request=req)

    def getViewHTML(self, maskitem, nodes, flags, language=None, template_from_caller=None, mask=None, use_label=True):
        if flags & VIEW_DATA_ONLY:
            ret = []
            for item in maskitem.getChildren().sort_by_orderpos():
                f = getMetadataType(item.get("type"))
                ret.append(f.getViewHTML(item, nodes, flags, language=language))
            return ret
        else:
            if use_label:
                snippets = [
                        """
                            <div class="mask_row hgroup hgroup-{}">
                                <div class="mask_label">{}: </div>
                                <div class="mask_value">
                        """.format(
                            maskitem.id,
                            _utils_utils.esc(maskitem.getLabel()),
                        )
                    ]
            else:
                snippets = ['<div class="mask_row hgroup hgroup-%s"><div class="mask_value">' % (maskitem.id)]
            raw_values = ['&nbsp;']
            sep = ''
            has_raw_value = False  # skip group display if no item has raw_value
            items = maskitem.getChildren().sort_by_orderpos()
            for i, item in enumerate(items):
                f = getMetadataType(item.get("type"))
                raw_value = f.getViewHTML(item, nodes, flags | VIEW_SUB_ELEMENT, language=language)
                if raw_value.strip():
                    raw_values.append(raw_value)
                    if not raw_value == '&nbsp;':
                        has_raw_value = True
                    if sep:
                        snippets.append(sep)
                        sep = item.get('separator', '&nbsp;')
                    snippets.append('<span class="hgroup_item">%s</span>' % raw_value)
                else:
                    sep = ''  # no separator before or after empty sub element

            unit = maskitem.get('unit').strip()
            if not has_raw_value:
                snippets = []  # no value when all sub elements are empty
            elif raw_values and unit:
                snippets.append('&nbsp;<span class="hgroup_unit field_unit hgroup-%s">%s</span></div></div>' % (maskitem.id, unit))
            elif raw_values:
                snippets.append('</div></div>')
            ret = ''.join(snippets)
            return ret

    def getMetaHTML(self, parent, index, sub=False, language=None, fieldlist={}):
        item = parent.children.order_by(Node.orderpos)[index]

        html_form = u"".join(
            _itertools.imap(
                u"<div id='hitem'>{}</div>".format,
                (
                    getMetadataType(field.get("type")).getMetaHTML(
                        item,
                        idx,
                        True,
                        language=language,
                        fieldlist=fieldlist,
                    ) for idx, field in enumerate(item.children.order_by(Node.orderpos))
                ),
            )
        )

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
            file="schema/mask/hgroup.html",
            macro="admin_get_field_for_maskedit",
        )

    def getMetaEditor(self, item, req):
        """ editor mask for hgroup-field definition """
        fieldlist = getAllMetaFields()
        if len(item.getParents()) == 0:
            pid = req.params.get("pid", "")
        else:
            pid = item.getParents()[0].id

        if ustr(req.params.get("edit")) == ustr("None"):
            item = Maskitem(name="", type="maskitem")
            item.set("type", "hgroup")

        details = ""
        i = 0
        for field in item.getChildren().sort_by_orderpos():
            f = getMetadataType(field.get("type"))
            details += f.getMetaHTML(item, i, False, fieldlist=fieldlist)
            i += 1

        if req.params.get("sel_id", "") != "":
            i = 0
            for id in req.params.get("sel_id")[:-1].split(";"):
                f = getMetadataType(q(Node).get(id).get("type"))
                details += f.getMetaHTML(
                        item,
                        i,
                        False,
                        itemlist=req.params.get("sel_id")[:-1].split(";"),
                        ptype="hgroup",
                        fieldlist=fieldlist,
                        language=_core_translation.set_language(req.accept_languages),
                    )
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
        return _tal.processTAL(v, file="schema/mask/hgroup.html", macro="metaeditor", request=req)
