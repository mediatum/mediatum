"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Peter Heckl <heckl@ub.tum.de>

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
from core.metatype import Metatype, charmap

class m_htmlmemo(Metatype):
    
    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):
        return athana.getTAL("metadata/htmlmemo.html", {"lock":lock, "value":value, "width":width, "name":field.getName(), "field":field}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/htmlmemo.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";","; ")
        return (field.getLabel(), value)

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        value = ""
        if field:
            value = field.getValues()
        return athana.getTAL("metadata/htmlmemo.html", {"value":value}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_htmlmemo"
        
    def getInformation(self):
        return {"moduleversion":"1.0", "softwareversion":"1.1"}
        
    # method for additional keys of type memo
    def getLabels(self):
        return m_htmlmemo.labels

    labels = { "de":
            [
                ("editor_memo_label","Zeichen \xc3\xbcbrig"),
                ("mask_edit_max_length","Maximall\xc3\xa4nge"),
                ("fieldtype_htmlmemo", "HTML Memofeld"),
                ("htmlmemo_titlepopupbutton", "Editiermaske \xc3\xb6ffnen"),
                ("htmlmemo_popup_title", "Eingabemaske f\xc3\xbcr HTML formatierte Texte"),
                ("htmlmemo_valuelabel", "Wert:"),
            ],
           "en":
            [
                ("editor_htmlmemo_label", "characters remaining"),
                ("mask_edit_max_length","Max. length"),
                ("fieldtype_htmlmemo", "html memo"),
                ("htmlmemo_titlepopupbutton", "open editor mask"),
                ("htmlmemo_popup_title", "Editor mask for HTML formatted text"),
                ("htmlmemo_valuelabel", "Value:"),
            ]
         }
