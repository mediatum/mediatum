"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2009 Matthias Kramm <kramm@in.tum.de>

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
from core.metatype import Metatype

class m_message(Metatype):
    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        value = value.split(";")
        while len(value)<5:
            value.append("0")           
        return athana.getTAL("metadata/message.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/message.html",{"context":context}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";","; ").split(";")
        if int(value[1])==0: # suppress label
            return ("","")

        ret = '<span style="color: '+value[2]+'">'+value[0]+'</span>'

        if int(value[3])==1: #bold
            ret = '<b>'+ret+'</b>'
        elif int(value[3])==2: #italic
            ret = '<i>'+ret+'</i>'
        elif int(value[3])==3: # bold+italic
            ret = '<b><i>'+ret+'</i></b>'
        return ("", ret)

    def getName(self):
        return "fieldtype_message"
