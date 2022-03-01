# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os.path
import codecs
from werkzeug.datastructures import ImmutableMultiDict
from mediatumtal import tal
from core import Node, db
from utils.utils import esc
from core.metatype import Metatype, Context


logg = logging.getLogger(__name__)

q = db.query

class m_mlist(Metatype):

    name = "mlist"

    def formatValues(self, context):
        valuelist = []

        items = {}
        try:
            n = context.collection
            if n is not None:
                field_name = context.field.getName()
                id_attr_val = n.all_children_by_query(q(Node.id, Node.a[field_name]).filter(Node.a[field_name] != None and Node.a[field_name] != '').distinct(Node.a[field_name]))
                items = {pair[0]: pair[1] for pair in id_attr_val}
        except:
            None

        tempvalues = context.field.getValueList()
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

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        context = Context(field, value=value, width=width, name=field.getName(), lock=lock, language=language)
        return tal.getTAL("metadata/mlist.html", {"context": context,
                                                  "valuelist": self.formatValues(context),
                                                  "required": 1 if required else None,
                                                  },
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/mlist.html",
                          {"context": context,
                           "valuelist": self.formatValues(context)},
                          macro="searchfield",
                          language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        if isinstance(params, ImmutableMultiDict):
            valuelist = params.getlist(item)
            value = ";".join(valuelist)
        else:
            value_unprepared = params.get(item)
            value = value_unprepared.replace("; ", ";")
        return value

    def get_metafieldeditor_html(self, field, metadatatype, language):
        return tal.getTAL("metadata/mlist.html", dict(value=field.getValues()), macro="metafieldeditor", language=language)


    translation_labels = dict(
        de=dict(
            mlist_list_values="Listenwerte:",
            fieldtype_mlist="Mehrfachauswahl",
            fieldtype_mlist_desc="Werte-Auswahlfeld als Multiselect-Liste",
        ),
        en=dict(
            mlist_list_values="List values:",
            fieldtype_mlist="multilist",
            fieldtype_mlist_desc="selection list for multiple values",
        ),
    )
