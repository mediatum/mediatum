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
import core.tree as tree
from schema.schema import VIEW_DATA_ONLY, VIEW_DEFAULT
from core.tree import Node, getNode
from core.metatype import Metatype


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
        item = parent.getChildren().sort()[index]
        ret = ''
        if not sub:
            ret += '<div id="' + item.id + '" class="row" onmouseover="pick(this)" onmouseout="unpick(this)" onclick="select(this)">'
        ret += '<b>' + str(item.getLabel()) + '</b>'

        if not sub:
            ret += '<div align="right" id="' + item.id + '_sub" style="display:none"><small style="color:silver">(' + (item.get("type")) + ')</small>'
            if index > 0:
                ret += '<input type="image" src="/img/uparrow.png" name="up_' + str(item.id) + '" i18n:attributes="title mask_edit_up_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            if index < len(parent.getChildren()) - 1:
                ret += '<input type="image" src="/img/downarrow.png" name="down_' + str(item.id) + '" i18n:attributes="title mask_edit_down_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            ret += ' <input type="image" src="/img/edit.png" name="edit_' + str(item.id) + '" i18n:attributes="title mask_edit_edit_row"/> <input type="image" src="/img/delete.png" name="delete_' + str(item.id) + '" i18n:attributes="title mask_edit_delete_row" onClick="return questionDel()"/></div>'
            ret += '</div>'

        return ret

    def getMetaEditor(self, item, req):
        """ editor mask for label definition """
        fields = []
        metadatatype = req.params.get("metadatatype")

        if req.params.get("op", "") == "new":
            pidnode = tree.getNode(req.params.get("pid"))
            if pidnode.get("type") in ("vgroup", "hgroup"):
                for field in pidnode.getAllChildren():
                    if field.getType().getName() == "maskitem" and field.id != pidnode.id:
                        fields.append(field)
            else:
                for m in metadatatype.getMasks():
                    if str(m.id) == str(req.params.get("pid")):
                        for field in m.getChildren():
                            fields.append(field)
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))

        v = {}
        v["op"] = req.params.get("op", "")
        v["pid"] = req.params.get("pid", "")
        v["item"] = item
        v["fields"] = fields
        return req.getTAL("schema/mask/label.html", v, macro="metaeditor")

    def getEditorHTML(self, field, value="", width=40, name="", lock=0, language=None):
        return athana.getTAL("metadata/label.html", {"lock": lock, "value": value, "width": width, "name": name, "field": field}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/label.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1, template_from_caller=None, mask=None):
        value = node.get(field.getName())
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def isContainer(self):
        return True

    def getName(self):
        return "maskfieldtype_label"

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
