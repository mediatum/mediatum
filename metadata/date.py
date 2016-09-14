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
import re
from mediatumtal import tal
import utils.date as date
from utils.date import format_date, parse_date, validateDate
from core.metatype import Metatype
from schema.schema import dateoption


logg = logging.getLogger(__name__)


class m_date(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        d = field.getSystemFormat(field.getValues())

        if value == "?":
            value = date.format_date(date.now(), d.getValue())
        try:
            value = date.format_date(date.parse_date(value), d.getValue())
        except:
            pass

        return tal.getTAL("metadata/date.html", {"lock": lock,
                                                 "value": value,
                                                 "width": width,
                                                 "name": field.getName(),
                                                 "field": field,
                                                 "pattern": self.get_input_pattern(field),
                                                 "title": self.get_input_title(field),
                                                 "placeholder": self.get_input_placeholder(field),
                                                 "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        context.value = context.value.split(";")
        while len(context.value) < 2:
            context.value.append('')
        return tal.getTAL("metadata/date.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        ''' search with re if string could be a date
            appends this to a list and returns this

            :param metafield: metadatafield
            :param node: node with fields
            :return: formatted value
        '''
        value = node.get(metafield.getName())

        if not value or value == "0000-00-00T00:00:00":  # dummy for unknown
            return (metafield.getLabel(), u"")
        else:
            try:
                d = parse_date(value)
            except ValueError:
                return (metafield.getLabel(), value)
            value = format_date(d, format=metafield.getValues())

        value_list = []

        if re.search(r'\d{2}\W\d{2}\W', value):
            day_month = re.sub(r'00\W', '', re.search(r'\d{2}\W\d{2}\W', value).group())
            value_list.append(day_month)

        if re.search(r'\d{4}\W\d{2}', value):
            year_month = re.sub(r'\W00', '', re.search(r'\d{4}-\d{2}', value).group())
            value_list.append(year_month)
        elif re.search(r'\d{4}', value):
            value_list.append(re.search(r'\d{4}', value).group())

        return (metafield.getLabel(), ''.join(value_list))

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        f = field.getSystemFormat(ustr(field.getValues()))
        if not f:
            return ""
        try:
            d = parse_date(ustr(value), f.getValue())
        except ValueError:
            return ""
        if not validateDate(d):
            return ""
        return format_date(d, format='%Y-%m-%dT%H:%M:%S')

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            value = field.getValues()
        except AttributeError:
            value = u""
        return tal.getTAL("metadata/date.html", {"value": value, "dateoption": dateoption}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_date"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    # method for additional keys
    def getLabels(self):
        return m_date.labels

    def get_input_pattern(self, field):
        regexes = {date.getShortName(): date.get_validation_regex() for date in dateoption}
        try:
            return regexes[field.getValues()]
        except KeyError:
            return regexes[0]  # format: dd.mm.yyyy

    def get_input_title(self, field):
        return field.getValues()

    def get_input_placeholder(self, field):
        return field.getValues()

    labels = {"de":
              [
                  ("date_edit_date_format", "Datums-/Zeitformat:"),
                  ("fieldtype_date", "Datum"),
                  ("fieldtype_date_desc", "Datumsauswahl (Tag / Monat / Jahr)")
              ],
              "en":
              [
                  ("date_edit_date_format", "Date-/Time-format:"),
                  ("fieldtype_date", "date"),
                  ("fieldtype_date_desc", "date field (day / month / year)")
              ]
              }
