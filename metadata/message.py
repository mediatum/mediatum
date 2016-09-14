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
from mediatumtal import tal
from core.metatype import Metatype


class m_message(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        value = value.split(";")
        if len(value) < 2:
            value = ["", 0, "black", 0]
        return tal.getTAL("metadata/message.html", {"lock": lock,
                                                    "value": value,
                                                    "width": width,
                                                    "name": field.getName(),
                                                    "field": field,
                                                    "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/message.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ").split(";")
        if len(value) < 2:
            value = ["", 0, "black", 0]
        if int(value[1]) == 0:  # suppress label
            return ("", "")

        ret = u'<span style="color: ' + value[2] + '">' + value[0] + '</span>'

        if int(value[3]) == 1:  # bold
            ret = '<b>' + ret + '</b>'
        elif int(value[3]) == 2:  # italic
            ret = '<i>' + ret + '</i>'
        elif int(value[3]) == 3:  # bold+italic
            ret = '<b><i>' + ret + '</i></b>'
        return ("", ret)

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1", "files": "meta.py;meta.html"}

    def getName(self):
        return "fieldtype_message"

    # method for additional keys of type message
    def getLabels(self):
        return m_message.labels

    labels = {"de":
              [
                  ("fieldtype_message", "Meldung"),
                  ("fieldtype_message_desc", "Meldungs- oder Hinweiszeile")
              ],
              "en":
              [
                  ("fieldtype_message", "message"),
                  ("fieldtype_message_desc", "message or notice field")
              ]
              }
