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
import core.tree as tree
from utils.utils import esc
from core.metatype import Metatype, Context

class m_mlist(Metatype):

    def formatValues(self, context):
        valuelist = []

        items = {}
        try:
            n = tree.getNode(context.collection)
            items = n.getAllAttributeValues(context.field.getName(), context.access)
        except tree.NoSuchNodeError:
            None

        value = context.value.split(";")       
        for val in context.field.getValueList():
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
            
            if val in items.keys():
                num = int(items[val])

            try:
                if int(num)<0:
                    raise ""
                elif int(num)==0:
                    num = ""
                else:
                    num = " ("+str(num)+")"
            except:
                num = ""
                
            val = esc(val)

            if not canbeselected:
                valuelist.append(("optgroup", "<optgroup label=\""+indentstr+val+"\">","", ""))
            elif (val in value):
                valuelist.append(("optionselected", indentstr, val, num))
            else:
                valuelist.append(("option", indentstr, val, num))
        return valuelist

        
    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):    
        context = Context(field, value=value, width=width, name=name, lock=lock, language=language)
        return athana.getTAL("metadata/mlist.html", {"context":context, "valuelist":self.formatValues(context)}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/mlist.html",{"context":context, "valuelist":self.formatValues(context)}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None):
        value = esc(node.get(field.getName()).replace(";","; "))
        return (field.getLabel(), value)

    def getFormatedValueForDB(self, field, value):
        return value.replace("; ",";")

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        return athana.getTAL("metadata/mlist.html", {"value":value}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_mlist"
