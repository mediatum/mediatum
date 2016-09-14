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
import logging
from mediatumtal import tal
from core.metatype import Metatype
from core import Node
from lib.iptc.IPTC import get_wanted_iptc_tags
logg = logging.getLogger(__name__)


class m_meta(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/meta.html", {"lock": lock,
                                                 "value": value,
                                                 "width": width,
                                                 "name": field.getName(),
                                                 "field": field},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/meta.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        return (metafield.getLabel(), node.get(metafield.getValues()))

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            value = field.getValues().split("\r\n")
        except AttributeError:
            #value = u""
            value = []
            while len(value) < 2:
                value.append('')

        attr = {}
        if metadatatype:
            for t in metadatatype.getDatatypes():
                content_class = Node.get_class_for_typestring(t)
                node = content_class(name=u'')
                try:
                    attr.update(node.getTechnAttributes())
                    attr['IPTC'] = get_wanted_iptc_tags()
                except AttributeError:
                    logg.exception("attribute error in getMaskEditorHTML, continue")
                    continue

        return tal.getTAL("metadata/meta.html", {"value": value, "t_attrs": attr}, macro="maskeditor", language=language)

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1", "files": "meta.py;meta.html"}

    def getName(self):
        return "fieldtype_meta"

    # method for additional keys of type meta
    def getLabels(self):
        return m_meta.labels

    labels = {"de":
              [
                  ("metafield_tech_meta", "Technisches Metadatenfeld:"),
                  ("metafield_metadata_field", "Metadatenfeld"),
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
