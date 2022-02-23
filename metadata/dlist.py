# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import urllib2
import json

from mediatumtal import tal
from utils.utils import esc, suppress
from core.metatype import Metatype
from core import Node
from core import db
from contenttypes import Home, Collections
from core.systemtypes import Root

q = db.query

logg = logging.getLogger(__name__)


class m_dlist(Metatype):
    def formatValues(self, context):
        valuelist = []

        items = {}
        try:
            n = context.collection
            if not isinstance(n, Node):
                raise KeyError
            field_name = context.field.getName()
            id_attr_val = n.all_children_by_query(q(Node.id, Node.a[field_name]).filter(Node.a[field_name] != None and Node.a[field_name] != '').distinct(Node.a[field_name]))
            items = {pair[0]: pair[1] for pair in id_attr_val}
        except KeyError:
            None

        value = context.value.split(";")

        for val in context.field.getValueList():
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
                    raise u""
                elif int(num) == 0:
                    num = u""
                else:
                    num = u" (" + unicode(num) + u")"
            except:
                logg.exception("exception in formatValues, using empty string")
                num = u""

            val = esc(val)

            if not canbeselected:
                valuelist.append(("optgroup", "<optgroup label=\"" + indentstr + val + "\">", "", ""))
            elif (val in value):
                valuelist.append(("optionselected", indentstr, val, num))
            else:
                valuelist.append(("option", indentstr, val, num))
        return valuelist

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None, required=None):
        fielddef = field.getValues().split("\r\n")  # url(source), type, name variable, value variable
        if name == "":
            name = field.getName()
        while len(fielddef) < 5:
            fielddef.append("")

        valuelist = []
        with suppress(ValueError, warn=False):
            # enables the field to be added without fields filled in without throwing an exception
            if fielddef[1] == 'json':
                opener = urllib2.build_opener()
                f = opener.open(urllib2.Request(fielddef[0], None, {}))
                data = json.load(f)
                data.sort(lambda x, y: cmp(x[fielddef[2]], y[fielddef[2]]))
                for item in data:
                    valuelist.append({'select_text': fielddef[4].replace(fielddef[2], item[fielddef[2]]).replace(
                        fielddef[3], item[fielddef[3]]), 'select_value': item[fielddef[3]]})
                f.close()
            elif fielddef[1] == 'list':
                opener = urllib2.build_opener()
                f = opener.open(urllib2.Request(fielddef[0], None, {}))
                for item in f.read().split("\n"):
                    if not item.startswith("#"):
                        if ";" in item:
                            _v, _t = item.split(";")
                        else:
                            _v = _t = item
                        valuelist.append({'select_text': _t.strip(), 'select_value': _v.strip()})
                f.close()
        return tal.getTAL("metadata/dlist.html", {"lock": lock,
                                                  "name": name,
                                                  "width": width,
                                                  "value": value,
                                                  "valuelist": valuelist,
                                                  "fielddef": fielddef,
                                                  "required": 1 if required else None,
                                                  },
                          macro="editorfield",
                          language=language)


    def getSearchHTML(self, context):
        return tal.getTAL("metadata/dlist.html",
                          {"context": context,
                           "valuelist": filter(lambda x: x != "",
                                               self.formatValues(context))},
                          macro="searchfield",
                          language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def get_metafieldeditor_html(self, field, metadatatype, language):
        value = field.getValues().split("\r\n")
        value.extend(("",)*5)
        value = value[:5] # url(source), name variable, value variable
        return tal.getTAL("metadata/dlist.html", {"value": value,
                                                  "types": ['json', 'list']},
                          macro="maskeditor",
                          language=language)

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    translation_labels = dict(
        de=dict(
            dlist_list_values="Dynamische Listenwerte:",
            fieldtype_dlist="Dynamische Werteliste",
            fieldtype_dlist_desc="Werte-Auswahlfeld als Drop-Down Liste",
            dlist_edit_source="Adresse der Daten:",
            dlist_edit_type="Typ der Daten:",
            dlist_edit_attr="Attribut-Variable:",
            dlist_edit_valattr="Werte-Variable:",
            dlist_type_json="Json:",
            dlist_type_list="Liste:",
            dlist_edit_format="Anzeigeformat:",
        ),
        en=dict(
            dlist_list_values="Dynamic List values:",
            fieldtype_dlist="dynamic valuelist",
            fieldtype_dlist_desc="drop down valuelist",
            dlist_edit_source="address of data:",
            dlist_edit_type="type of data:",
            dlist_edit_attr="attribute variable:",
            dlist_edit_valattr="value variable:",
            dlist_type_json="Json:",
            dlist_type_list="List:",
            dlist_edit_format="format in selection:",
        ),
    )
