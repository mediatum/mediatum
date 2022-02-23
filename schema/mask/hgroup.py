# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import mediatumtal.tal as _tal

import core.translation as _core_translation
from schema.schema import getMetadataType, getAllMetaFields, VIEW_DATA_ONLY, VIEW_SUB_ELEMENT, Maskitem
from core.metatype import Metatype
from core import Node, db

q = db.query


class m_hgroup(Metatype):

    def getFormHTML(self, field, nodes, req):
        cls = "editorrow"
        for item in field.getChildren().sort_by_orderpos():
            if item.getField().id in req.params.get("errorlist", []):
                cls = "editorerror"
                break
        ret = '<div class="' + cls + '">'

        ret += '<div class="mask_label">' + field.getLabel() + '</div>'

        for item in field.getChildren().sort_by_orderpos():
            f = getMetadataType(item.get("type"))
            ret += f.getFormHTML(item, nodes, req, True)
        return ret + '</div>'

    def getViewHTML(self, maskitem, nodes, flags, language=None, template_from_caller=None, mask=None, use_label=True):
        if flags & VIEW_DATA_ONLY:
            ret = []
            for item in maskitem.getChildren().sort_by_orderpos():
                f = getMetadataType(item.get("type"))
                ret.append(f.getViewHTML(item, nodes, flags, language=language))
            return ret
        else:
            if use_label:
                snippets = ['<div class="mask_row hgroup hgroup-%s"><div class="mask_label">%s: </div><div class="mask_value">' % (maskitem.id, maskitem.getLabel())]
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
        item = parent.getChildren().sort_by_orderpos()[index]
        ret = ''
        i = 0

        if not sub:
            ret += '<div id="{}" class="row metaeditor" onmouseover="pick(this)" onmouseout="unpick(this)" onclick="select(this)">'.format(item.id)

        ret += '<fieldset>'

        if item.getLabel() != "":
            ret += u'<legend>{}</legend>'.format(item.getLabel())

        ret += '<div id="editor_content">'
        for field in item.getChildren().sort_by_orderpos():
            f = getMetadataType(field.get("type"))
            ret += u'<div id="hitem">{}</div>'.format(f.getMetaHTML(item, i, True, language=language, fieldlist=fieldlist))
            i += 1

        if len(item.getChildren()) == 0:
            ret += '<span i18n:translate="mask_editor_no_fields">- keine Felder definiert -</span>'

        ret += '</fieldset>'

        if not sub:
            ret += '<div align="right" id="' + unicode(item.id) + \
                '_sub" style="display:none; clear:both"><small style="color:silver">(' + (item.get("type")) + ')</small>'
            if index > 0:
                ret += '<input type="image" src="/img/uparrow.png" name="up_' + \
                    unicode(item.id) + '" i18n:attributes="title mask_edit_up_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            if index < len(parent.getChildren()) - 1:
                ret += '<input type="image" src="/img/downarrow.png" name="down_' + \
                    unicode(item.id) + '" i18n:attributes="title mask_edit_down_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            ret += ' <input type="image" src="/img/edit.png" name="edit_' + unicode(
                item.id) + '" i18n:attributes="title mask_edit_edit_row"/> <input type="image" src="/img/delete.png" name="delete_' + unicode(
                item.id) + '" i18n:attributes="title mask_edit_delete_row" onClick="return questionDel()"/></div>'
            ret += '</div>'

        return ret

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
