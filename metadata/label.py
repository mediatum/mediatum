# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
from schema.schema import VIEW_DATA_ONLY, VIEW_DEFAULT
from core.metatype import Metatype
from core import Node
from core import db
from utils.utils import esc

q = db.query

class m_label(Metatype):

    name = "label"

    def getFormHTML(self, field, nodes, req):
        return '<b>' + field.getLabel() + '</b><br/>'

    def getViewHTML(self, field, nodes, flags, language=None, template_from_caller=None, mask=None):
        if flags & VIEW_DATA_ONLY:
            return []
        elif flags & VIEW_DEFAULT:
            # default view
            return '<b>' + field.getLabel() + '</b><br/>'
        else:
            return '<br/>'

    def getMetaHTML(self, parent, index, sub=False, language=None, fieldlist={}):
        """ return formated row for metaeditor """
        item = parent.getChildren().sort_by_orderpos()[index]
        ret = ''
        if not sub:
            ret += '<div id="' + ustr(item.id) + '" class="row" onmouseover="pick(this)" onmouseout="unpick(this)" onclick="select(this)">'
        ret += '<b>' + ustr(item.getLabel()) + '</b>'

        if not sub:
            ret += '<div align="right" id="' + ustr(item.id) + \
                '_sub" style="display:none"><small style="color:silver">(' + (item.get("type")) + ')</small>'
            if index > 0:
                ret += '<input type="image" src="/img/uparrow.png" name="up_' + \
                    ustr(item.id) + '" i18n:attributes="title mask_edit_up_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            if index < len(parent.getChildren()) - 1:
                ret += '<input type="image" src="/img/downarrow.png" name="down_' + \
                    ustr(item.id) + '" i18n:attributes="title mask_edit_down_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            ret += ' <input type="image" src="/img/edit.png" name="edit_' + ustr(
                item.id) + '" i18n:attributes="title mask_edit_edit_row"/> <input type="image" src="/img/delete.png" name="delete_' + ustr(
                item.id) + '" i18n:attributes="title mask_edit_delete_row" onClick="return questionDel()"/></div>'
            ret += '</div>'

        return ret

    def getMetaEditor(self, item, req):
        """ editor mask for label definition """
        fields = []
        metadatatype = req.params.get("metadatatype")

        if req.params.get("op", "") == "new":
            pidnode = q(Node).get(req.params.get("pid"))
            if pidnode.get("type") in ("vgroup", "hgroup"):
                for field in pidnode.all_children:
                    if field.type == "maskitem" and field.id != pidnode.id:
                        fields.append(field)
            else:
                for m in metadatatype.getMasks():
                    if ustr(m.id) == ustr(req.params.get("pid")):
                        for field in m.children:
                            fields.append(field)
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))

        v = {}
        v["op"] = req.params.get("op", "")
        v["pid"] = req.params.get("pid", "")
        v["item"] = item
        v["fields"] = fields
        return tal.processTAL(v, file="metadata/label.html", macro="metaeditor", request=req)

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        return tal.getTAL("metadata/label.html", {"lock": lock,
                                                  "value": value,
                                                  "width": width,
                                                  "name": field.getName(),
                                                  "field": field},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/label.html",
                dict(name=name, value=value),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)


    translation_labels = dict(
        de=dict(
            fieldtype_label="Label",
            fieldtype_label_desc="Text als String",
        ),
        en=dict(
            fieldtype_label="label field",
            fieldtype_label_desc="text without input field",
        ),
    )
