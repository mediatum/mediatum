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
import core.athana as athana
from utils.utils import esc
from core.metatype import Metatype

class m_label(Metatype):

    def getEditorHTML(self, field, value="", width=40, name="", lock=0, language=None):
        return athana.getTAL("metadata/label.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/label.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1, template_from_caller=None, mask=None):
        value = node.get(field.getName())
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def getName(self):
        return "fieldtype_label"
        
    def getInformation(self):
        return {"moduleversion":"1.0", "softwareversion":"1.1"}

    # method for additional keys of type text
    def getLabels(self):
        return m_label.labels

    labels = { "de":
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
