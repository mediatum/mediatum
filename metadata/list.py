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

#from core.tree import getNode

class m_list(Metatype):
    def formatValues(self, context):
        valuelist = []

        items = {}
        try:
            n = context.collection
            if n is None:
                raise tree.NoSuchNodeError()
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
            
            num =0
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
        return athana.getTAL("metadata/list.html", {"context":context, "valuelist":filter(lambda x:x!="", self.formatValues(context))}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return athana.getTAL("metadata/list.html", {"context":context, "valuelist":filter(lambda x:x!="", self.formatValues(context))}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName())
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        return athana.getTAL("metadata/list.html", {"value":value}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_list"
        
    def getInformation(self):
        return {"moduleversion":"1.1", "softwareversion":"1.1"}
        
    # method for additional keys of type list
    def getLabels(self):
        return m_list.labels

    labels = { "de":
            [
                ("list_list_values", "Listenwerte:"),
                ("fieldtype_list", "Werteliste"),
                ("fieldtype_list_desc", "Werte-Auswahlfeld als Drop-Down Liste")
            ],
           "en":
            [
                ("list_list_values", "List values:"),
                ("fieldtype_list", "valuelist"),
                ("fieldtype_list_desc", "drop down valuelist")
            ]
          }
