# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import contextlib as _contextlib
import itertools as _itertools
import logging
import operator as _operator
import urllib2
import json

from mediatumtal import tal

import metadata.ilist as _ilist
from utils.utils import esc, suppress
from core.metatype import Metatype
from core import Node
from core import db
from contenttypes import Home, Collections
from core.systemtypes import Root

q = db.query

logg = logging.getLogger(__name__)


def _download_list(url, format_, key_attr, key_value, display_format):
    """
    Download the list from the `url`.
    `format_` may be "json" or "list".
    "json" assumes a list of dicts:
    From each dict, the elements with names `key_attr`
    and `_key_value` will be extracted ando
    injected into the string `display_format` in
    those places where the respective keys are.
    "list" format will just drop comments,
    and try to split at ";".
    Results are yielded as individual dicts with
    `select_text` and `select_value` keys.
    """
    with _contextlib.closing(urllib2.urlopen(url)) as data:
        if format_=="list":
            for item in data:
                item = item.rstrip("\n")
                if item.startswith("#"):
                    continue
                if ";" in item:
                    text, value = item.split(";", maxsplit=1)
                else:
                    text = value = item
                yield dict(select_text=text, select_value=value)
            return
        assert format_=="json"
        data = json.load(data)
    data.sort(key=_operator.itemgetter(key_attr))
    for item in data:
        yield dict(
                select_text=display_format.replace(key_attr, item[key_attr]).replace(key_value, item[key_value]),
                select_value=item[key_value],
               )


class m_dlist(Metatype):

    name = "dlist"

    def formatValues(self, n, field, value):
        items = {}
        try:
            if not isinstance(n, Node):
                raise KeyError
            field_name = field.getName()
            id_attr_val = _ilist.count_list_values_for_all_content_children(n.id, field_name)
            items = {pair[0]: pair[1] for pair in id_attr_val}
        except KeyError:
            None

        value = value.split(";")

        fielddef = field.getValues().split("\r\n")  # url(source), type, name variable, value variable
        while len(fielddef) < 5:
            fielddef.append("")
        for val in _itertools.imap(_operator.itemgetter("select_value"), _download_list(*fielddef[:5])):
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
                yield ("optgroup", "<optgroup label=\"" + indentstr + val + "\">", "", "")
            elif (val in value):
                yield ("optionselected", indentstr, val, num)
            else:
                yield ("option", indentstr, val, num)

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None, required=None):
        fielddef = field.getValues().split("\r\n")  # url(source), type, name variable, value variable
        while len(fielddef) < 5:
            fielddef.append("")
        valuelist = []
        with suppress(ValueError, warn=False):
            valuelist = list(_download_list(*fielddef[:5]))

        if name == "":
            name = field.getName()
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
                           "valuelist": self.formatValues(context.collection, context.field, context.value),
                          },
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
                          macro="metafieldeditor",
                          language=language)


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
