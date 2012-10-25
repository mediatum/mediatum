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
from utils.utils import esc
from core.metatype import Metatype, Context

class m_number(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):
        return athana.getTAL("metadata/number.html", {"lock":lock, "value":value, "width":width, "name":field.getName(), "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, context):
        return athana.getTAL("metadata/number.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";","; ")
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def getName(self):
        return "fieldtype_number"
        
    # method for additional keys of type number
    def getLabels(self):
        return m_number.labels

    labels = { "de":
            [
                ("fieldtype_number", "Zahl"),
                ("fieldtype_number_desc", "Feld zur Eingabe eines Zahlenwertes")
            ],
           "en":
            [
                ("fieldtype_number", "number"),
                ("fieldtype_number_desc", "field for digit input")   
            ]
         }

