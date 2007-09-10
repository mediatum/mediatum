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

class m_mlist(Metatype):

    def formatValues(self, field, value):
        valuelist = list()

        l = field.getValueList()
        if field.getFieldValueNum() is not None:
            numbers = field.getFieldValueNum().split(";")
        else:
            numbers = []

        if len(numbers) != len(l):
            numbers = [-1]*len(l)

        for val,num in zip(l,numbers):
            indent = 0
            canbeselected = 0
            while val.startswith("*"):
                val = val[1:]
                indent = indent + 1
            if val.startswith(" "):
                canbeselected = 1
            val = val.strip()
            if not indent:
                canbeselected = 1
            if indent>0:
                indent = indent-1
            indentstr = "&nbsp;"*(2*indent)

            try:
                if int(num)<0:
                    raise ""
                num = " ("+str(num)+")"
            except:
                num = ""

            if not canbeselected:
                valuelist.append(("optgroup", "<optgroup label=\""+indentstr+val+"\">"))
            else:
                if value != '' and val in value.split(';'):
                    valuelist.append(("optionselected", indentstr, val, num))
                else:
                    valuelist.append(("option", indentstr, val, num))
        return valuelist

        
    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):    
        return athana.getTAL("metadata/mlist.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field, "valuelist":self.formatValues(field,value)}, macro="editorfield", language=language)

    def getSearchHTML(self, field, value="", width=174, name="", language=None):
        return athana.getTAL("metadata/mlist.html",{"field":field, "value":value, "width":width, "name":name, "valuelist":self.formatValues(field,value)}, macro="searchfield", language=language)

    def getFormatedValue(self, field, node, language=None):
        value = esc(node.get(field.getName()).replace(";","; "))
        return (field.getLabel(), value)

    def getFormatedValueForDB(self, field, value):
        return value.replace("; ",";")

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        return athana.getTAL("metadata/mlist.html", {"value":value}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_mlist"
