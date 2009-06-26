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
import re
from utils.utils import esc
from core.metatype import Metatype,charmap

class m_text(Metatype):

    def getEditorHTML(self, field, value="", width=40, name="", lock=0, language=None):
        return athana.getTAL("metadata/text.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, context):
        return athana.getTAL("metadata/text.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";","; ")

        if html:
            value = esc(value)
            
        # replace variables
        for var in re.findall( r'&lt;(.+?)&gt;', value ):
            if var=="att:id":
                value = value.replace("&lt;"+var+"&gt;", node.id)
            elif var.startswith("att:"):
                val = node.get(var[4:])
                if val=="":
                    val = "____"

                value = value.replace("&lt;"+var+"&gt;", val)
        value = value.replace("&lt;", "<").replace("&gt;",">")
        return (field.getLabel(), value)

    def getFormatedValueForDB(self, field, value):
        try:
            return value.replace("; ",";")
        except:
            return value

    def getName(self):
        return "fieldtype_text"
        
    def getInformation(self):
        return {"moduleversion":"1.0", "softwareversion":"1.1"}
        
    
    # method for popup methods of type text
    def getPopup(self, req):
        req.writeTAL("metadata/text.html", {"charmap":charmap, "name":req.params.get("name"), "value":req.params.get("value")}, macro="popup")
        return athana.HTTP_OK
    
    # method for additional keys of type text
    def getLabels(self):
        return m_text.labels

    labels = { "de":
            [
                ("text_popup_title", "Eingabemaske f\xc3\xbcr Sonderzeichen"),
                ("fieldtype_text", "Textfeld"),
                ("fieldtype_text_desc", "Normales Texteingabefeld"),
                ("text_titlepopupbutton", "Editiermaske \xc3\xb6ffnen"),
                ("text_valuelabel", "Wert:"),
                ("text_formatedvalue", "Formatierter Wert:"),
                ("text_done", "\xC3\x9Cbernehmen"),
                ("text_cancel", "Abbrechen"),
                ("text_spcchar", "Sonderzeichen:"),
                ("text_bold_title", "Markierten Text 'Fett' setzen"),
                ("text_italic_title", "Markierten Text 'Kursiv' setzen"),
                ("text_sub_title", "Markierten Text 'tiefstellen'"),
                ("text_sup_title", "Markierten Text 'hochstellen'")
            ],
           "en":
            [
                ("text_popup_title", "Editor mask for specialchars"),
                ("fieldtype_text", "text field"),
                ("fieldtype_text_desc", "normal text input field"),
                ("text_titlepopupbutton", "open editor mask"),
                ("text_valuelabel", "Value:"),
                ("text_formatedvalue", "Formated Value:"),
                ("text_done", "Done"),
                ("text_cancel", "Cancel"),
                ("text_spcchar", "Special chars:"),
                ("text_bold_title", "set marked text 'bold'"),
                ("text_italic_title", "set marked text 'italic'"),
                ("text_sub_title", "set marked text 'subscript'"),
                ("text_sup_title", "set marked text 'superscript'")
            ]
         }
