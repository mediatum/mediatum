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
import core.athana as athana
from core.metatype import Metatype, charmap

class m_memo(Metatype):
    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        return athana.getTAL("metadata/memo.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/memo.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";","; ")
        return (field.getLabel(), value)

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        return athana.getTAL("metadata/memo.html", {"value":value}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_memo"
        
    def getInformation(self):
        return {"moduleversion":"1.1", "softwareversion":"1.1"}
        
    # method for popup methods of type memo
    def getPopup(self, req):
        req.writeTAL("metadata/memo.html", {"charmap":charmap, "name":req.params.get("name"), "value":req.params.get("value")}, macro="popup")
        return athana.HTTP_OK
           
    # method for additional keys of type memo
    def getLabels(self):
        return m_memo.labels

    labels = { "de":
            [
                ("editor_memo_label","Zeichen \xc3\xbcbrig"),
                ("mask_edit_max_length","Maximall\xc3\xa4nge"),
                ("fieldtype_memo", "Memofeld"),
                ("fieldtype_memo_desc", "Texteingabefeld beliebiger L\xc3\xa4nge"),
                ("memo_titlepopupbutton", "Editiermaske \xc3\xb6ffnen"),
                ("memo_popup_title", "Eingabemaske f\xc3\xbcr Sonderzeichen"),
                ("memo_valuelabel", "Wert:"),
                ("memo_formatedvalue", "Formatierter Wert:"),
                ("memo_done", "\xC3\x9Cbernehmen"),
                ("memo_cancel", "Abbrechen"),
                ("memo_spcchar", "Sonderzeichen:"),
                ("memo_bold_title", "Markierten Text 'Fett' setzen"),
                ("memo_italic_title", "Markierten Text 'Kursiv' setzen"),
                ("memo_sub_title", "Markierten Text 'tiefstellen'"),
                ("memo_sup_title", "Markierten Text 'hochstellen'")
            ],
           "en":
            [
                ("editor_memo_label", "characters remaining"),
                ("mask_edit_max_length","Max. length"),
                ("fieldtype_memo", "memo"),
                ("fieldtype_memo_desc", "textfield for any text length"),
                ("memo_titlepopupbutton", "open editor mask"),
                ("memo_popup_title", "Editor mask for specialchars"),
                ("memo_valuelabel", "Value:"),
                ("memo_formatedvalue", "Formated Value:"),
                ("memo_done", "Done"),
                ("memo_cancel", "Cancel"),
                ("memo_spcchar", "Special chars:"),
                ("memo_bold_title", "set marked text 'bold'"),
                ("memo_italic_title", "set marked text 'italic'"),
                ("memo_sub_title", "set marked text 'subscript'"),
                ("memo_sup_title", "set marked text 'superscript'")
            ]
         }
