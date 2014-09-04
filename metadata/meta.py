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
from mediatumtal import tal
import core.tree as tree
from core.metatype import Metatype

class m_meta(Metatype):
    
    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):
        return tal.getTAL("metadata/meta.html", {"lock":lock, "value":value, "width":width, "name":field.getName(), "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, context):
        return tal.getTAL("metadata/meta.html",{"context":context}, macro="searchfield", language=context.language)


    def getFormatedValue(self, field, node, language=None, html=1):
        return (field.getLabel(), node.get(field.getValues()))


    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            value = field.getValues()
        except:
            value = ""
        attr = {}
        if metadatatype:
            for t in metadatatype.getDatatypes():
                node = tree.Node(type=t)
                attr.update(node.getTechnAttributes())

        return tal.getTAL("metadata/meta.html", {"value":value, "t_attrs":attr}, macro="maskeditor", language=language)

    def getInformation(self):
        return {"moduleversion":"1.1", "softwareversion":"1.1", "files":"meta.py;meta.html"}
        
    def getName(self):
        return "fieldtype_meta"

    # method for additional keys of type meta
    def getLabels(self):
        return m_meta.labels

    labels = { "de":
            [
                ("metafield_tech_meta", "Technisches Metadatenfeld:"),
                ("metafield_metadata_field","Metadatenfeld"),
                ("fieldtype_meta", "Technisches Metadatum"),
                ("fieldtype_meta_desc", "Technisches Metadatum (automatisch vom System erstellt)")
            ],
           "en":
            [
                ("metafield_tech_meta", "Technical metadata field:"),
                ("fieldtype_meta", "technical metadata"),
                ("fieldtype_meta_desc", "field for technical metadata (automatically filled in by mediatum)")
            ]
          }    
