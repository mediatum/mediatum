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
import os.path
import codecs
from mediatumtal import tal
import core.tree as tree
from utils.utils import esc
from core.metatype import Metatype, Context


logg = logging.getLogger(__name__)


class m_mlist(Metatype):

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

        tempvalues = context.field.getValueList()
        valuesfiles = context.field.getFiles()

        if len(valuesfiles) > 0:  # a text file with list values was uploaded
            if os.path.isfile(valuesfiles[0].retrieveFile()):
                with codecs.open(valuesfiles[0].retrieveFile(), 'r', encoding='utf8') as valuesfile:
                    tempvalues = valuesfile.readlines()

        if tempvalues[0].find('|') > 0:  # there are values in different languages available
            languages = [x.strip() for x in tempvalues[0].split('|')]  # find out the languages
            valuesdict = dict((lang, []) for lang in languages)        # create a dictionary with languages as keys,
            # and list of respective values as dictionary values
            for i in range(len(tempvalues)):
                if i:  # if i not 0 - the language names itself shouldn't be included to the values
                    tmp = tempvalues[i].split('|')
                    for j in range(len(tmp)):
                        valuesdict[languages[j]].append(tmp[j])

            if not context.language:    # if there is no default language, the first language-value will be used
                context.language = languages[0]

            tempvalues = valuesdict[context.language]

        for val in tempvalues:
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
            if indent > 0:
                indent = indent - 1
            indentstr = "&nbsp;" * (2 * indent)

            if val in items.keys():
                num = int(items[val])

            try:
                if int(num) < 0:
                    raise u""
                elif int(num) == 0:
                    num = u""
                else:
                    num = u" (" + unicode(num) + u")"
            except:
                num = u""

            val = esc(val)

            if not canbeselected:
                valuelist.append(("optgroup", "<optgroup label=\"" + indentstr + val + "\">", "", ""))
            elif (val in context.value.split(";")):
                valuelist.append(("optionselected", indentstr, val, num))
            else:
                valuelist.append(("option", indentstr, val, num))

        return valuelist

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):
        context = Context(field, value=value, width=width, name=field.getName(), lock=lock, language=language)
        return tal.getTAL(
            "metadata/mlist.html", {"context": context, "valuelist": self.formatValues(context)}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/mlist.html",
                          {"context": context,
                           "valuelist": self.formatValues(context)},
                          macro="searchfield",
                          language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        return value.replace("; ", ";")

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        value = u""
        try:
            if field:
                value = field.getValues()
        except AttributeError:
            value = field
        return tal.getTAL("metadata/mlist.html", {"value": value}, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_mlist"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1", "files": "mlist.py;mlist.html"}

    # method for additional keys of type mlist
    def getLabels(self):
        return m_mlist.labels

    labels = {"de":
              [
                  ("list_list_values_file", "Datei mit Listenwerten:"),
                  ("mlist_list_values", "Listenwerte:"),
                  ("fieldtype_mlist", "Mehrfachauswahl"),
                  ("fieldtype_mlist_desc", "Werte-Auswahlfeld als Multiselect-Liste")
              ],
              "en":
              [
                  ("list_list_values_file", "Textfile with list values:"),
                  ("mlist_list_values", "List values:"),
                  ("fieldtype_mlist", "multilist"),
                  ("fieldtype_mlist_desc", "selection list for multiple values")
              ]
              }
