"""
 mediatum - a multimedia content repository

 Copyright (C) 2012 Arne Seifert <arne.seifert@tum.de>
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
from mediatumtal import tal
from schema.schema import VIEW_DATA_ONLY, VIEW_DEFAULT
from core.metatype import Metatype
from core import Node
from core import db
from utils.utils import esc

q = db.query

class m_label(Metatype):

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
        return req.getTAL("metadata/label.html", v, macro="metaeditor")

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        return tal.getTAL("metadata/label.html", {"lock": lock,
                                                  "value": value,
                                                  "width": width,
                                                  "name": field.getName(),
                                                  "field": field},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/label.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    @classmethod
    def isContainer(cls):
        return True

    def getName(self):
        return "fieldtype_label"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    # method for additional keys of type text
    def getLabels(self):
        return m_label.labels

    labels = {"de":
              [
                  ("fieldtype_label", "Label"),
                  ("fieldtype_label_desc", "Text als String"),
              ],
              "en":
              [
                  ("fieldtype_label", "label field"),
                  ("fieldtype_label_desc", "text without input field"),
              ]
              }
