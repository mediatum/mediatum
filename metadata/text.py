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
from core.metatype import Metatype

class m_text(Metatype):
    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        return athana.getTAL("metadata/text.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, field, value="", width=174, name="", language=None):
        return athana.getTAL("metadata/text.html",{"field":field, "value":value, "name":name}, macro="searchfield", language=language)

    def getFormatedValue(self, field, node, language=None):
        value = esc(node.get(field.getName()).replace(";","; "))
        
        # replace variables
        for var in re.findall( r'&lt;(.+?)&gt;', value ):
            if var=="att:id":
                value = value.replace("&lt;"+var+"&gt;", node.id)
            elif var.startswith("att:"):
                val = node.get(var[4:])
                if val=="":
                    val = "____"

                value = value.replace("&lt;"+var+"&gt;", val)

        return (field.getLabel(), value)

    def getFormatedValueForDB(self, field, value):
        try:
            return value.replace("; ",";")
        except:
            return value

    def getName(self):
        return "fieldtype_text"
