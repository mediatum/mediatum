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
import utils.date as date
from utils.date import format_date, parse_date, validateDate
from core.metatype import Metatype

class m_date(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):
        global dateoption

        d = field.getSystemFormat(str(field.getValues()))
            
        if value=="?":
            value = date.format_date(date.now(), d.getValue())
        try:
            value = date.format_date(date.parse_date(value),  d.getValue())
        except:
            pass

        return tal.getTAL("metadata/date.html", {"lock":lock, "value":value, "width":width, "name":field.getName(), "field":field}, macro="editorfield", language=language)


    def getSearchHTML(self, context):
        context.value = context.value.split(";")
        return tal.getTAL("metadata/date.html",{"context":context}, macro="searchfield", language=context.language)


    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName())
        
        if not value or value=="0000-00-00T00:00:00": # dummy for unknown
            return (field.getLabel(),"")
        else:
            try:
                d = parse_date(value)
            except ValueError:
                return (field.getLabel(),value)
            value = format_date(d, format=field.getValues())
        return (field.getLabel(), value)


    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        f = field.getSystemFormat(str(field.getValues()))
        if not f:
            return ""
        try:
            d = parse_date(str(value),f.getValue())
        except ValueError:
            return ""
        if not validateDate(d):
            return ""
        return format_date(d, format='%Y-%m-%dT%H:%M:%S')


    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            value = field.getValues()
        except:
            value = ""
        #value = ""
        #if field:
        #    value = field.getValues()
        return tal.getTAL("metadata/date.html", {"value":value, "dateoption":dateoption}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_date"
    
    def getInformation(self):
        return {"moduleversion":"1.1", "softwareversion":"1.1"}
        
    # method for additional keys
    def getLabels(self):
        return m_date.labels

    labels = { "de":
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
