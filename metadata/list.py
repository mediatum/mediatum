# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os
import codecs
from mediatumtal import tal

from utils.utils import esc
from core.metatype import Metatype, Context
from metadata.ilist import count_list_values_for_all_content_children
from core import Node
from core import db

q = db.query
logg = logging.getLogger(__name__)


class m_list(Metatype):

    def formatValues(self, context):
        valuelist = []
        items = {}
        try:
            n = context.collection
            if not isinstance(n, Node):
                raise KeyError
            field_name = context.field.getName()
            id_attr_val = count_list_values_for_all_content_children(n.id, field_name)
            items = {pair[0]: pair[1] for pair in id_attr_val}
        except KeyError:
            None

        tempvalues = context.field.getValueList()
        if len(tempvalues):  # Has the user entered any values?
            if tempvalues[0].find('|') > 0:  # there are values in different languages available
                languages = [x.strip() for x in tempvalues[0].split('|')]  # find out the languages
                valuesdict = dict((lang, []) for lang in languages)        # create a dictionary with languages as keys,
                # and list of respective values as dictionary values
                for i in range(len(tempvalues)):
                    if i:  # if i not 0 - the language names itself shouldn't be included to the values
                        tmp = tempvalues[i].split('|')
                        for j in range(len(tmp)):
                            valuesdict[languages[j]].append(tmp[j])

                lang = context.language
                # if there is no default language, the first language-value will be used
                if (not lang) or (lang not in valuesdict.keys()):
                    lang = languages[0]

                tempvalues = valuesdict[lang]

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

            num = 0
            if val in items.keys():
                num = int(items[val])

            try:
                if int(num) < 0:
                    raise Exception()
                elif int(num) == 0:
                    num = ""
                else:
                    num = " (" + ustr(num) + ")"
            except:
                logg.exception("exception in get_metafieldeditor_html, using empty string")
                num = ""

            val = esc(val)
            if not canbeselected:
                valuelist.append(("optgroup", "<optgroup label=\"" + indentstr + val + "\">", "", ""))
            elif (val in context.value.split(";")):
                valuelist.append(("optionselected", indentstr, val, num))
            else:
                valuelist.append(("option", indentstr, val, num))

        return valuelist

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        context = Context(field, value=value, width=width, name=field.getName(), lock=lock, language=language)
        return tal.getTAL("metadata/list.html", {"context": context,
                                                 "valuelist": filter(lambda x: x != "", self.formatValues(context)),
                                                 "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/list.html",
                          {"context": context,
                           "valuelist": filter(lambda x: x != "",
                                               self.formatValues(context))},
                          macro="searchfield",
                          language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        if field.get('multiple'):
            valuelist = params.getlist(item)
            value = ";".join(valuelist)
        else:
            value = params.get(item)
        return value.replace("; ", ";")

    def get_metafieldeditor_html(self, field, metadatatype, language):
        return tal.getTAL(
            "metadata/list.html",
            dict(value=field.getValues(), multiple_list=field.get('multiple')),
            macro="maskeditor",
            language=language,
        )

    def getName(self):
        return "fieldtype_list"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    # method for additional keys of type list
    def getLabels(self):
        return m_list.labels

    labels = {"de":
              [
                  ("list_multiple", "Mehrfachauswahl:"),
                  ("list_list_values", "Listenwerte:"),
                  ("fieldtype_list", "Werteliste"),
                  ("fieldtype_list_desc", "Werte-Auswahlfeld als Drop-Down Liste")
              ],
              "en":
              [
                  ("list_multiple", "Multiple choice:"),
                  ("list_list_values", "List values:"),
                  ("fieldtype_list", "valuelist"),
                  ("fieldtype_list_desc", "drop down valuelist")
              ]
              }
