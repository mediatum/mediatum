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
import core.search as search
import core.search.query
import core.tree as tree
from utils.utils import esc
from core.metatype import Metatype, Context


class m_ilist(Metatype):

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        return athana.getTAL("metadata/ilist.html", {"lock":lock, "value":value, "width":width, "name":name, "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, context):
        n = tree.getNode(context.collection)
        valuelist = n.getAllAttributeValues(context.field.getName(), context.access)
        keys = valuelist.keys()
        keys.sort()
        v = []
        for key in keys:
            v.append((key, valuelist[key]))
        return athana.getTAL("metadata/ilist.html",{"context":context, "valuelist":v}, macro="searchfield", language=context.language)


    def getFormatedValue(self, field, node, language=None):
        value = node.get(field.getName())
        try:
            if value[-1]==";":
                value = value[0:-1]
        except:
            pass
        value = esc(value.replace(";","; "))
        return (field.getLabel(), value)


    def getFormatedValueForDB(self, field, value, language=None):
        #value = value.replace(", ",";")
        return value

    def getName(self):
        return "fieldtype_ilist"
