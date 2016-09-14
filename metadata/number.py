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
from utils.utils import esc
from core.metatype import Metatype


class m_number(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/number.html", {"lock": lock,
                                                   "value": value,
                                                   "width": width,
                                                   "name": field.getName(),
                                                   "field": field,
                                                   "pattern": self.get_input_pattern(),
                                                   "title": self.get_input_title(),
                                                   "placeholder": self.get_input_placeholder(),
                                                   "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/number.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)



    def getName(self):
        return "fieldtype_number"

    # method for additional keys of type number
    def getLabels(self):
        return m_number.labels

    def get_input_pattern(self):
        return '^\d*$'

    def get_input_title(self):
        return 'Only digits are allowed.'

    def get_input_placeholder(self):
        return '#####'

    labels = {"de":
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
