# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os
import codecs
from mediatumtal import tal

import utils.utils as _utils
from utils.utils import esc
from core.metatype import Metatype, Context
from metadata.ilist import count_list_values_for_all_content_children
from core import Node
from core import db

q = db.query
logg = logging.getLogger(__name__)


class m_list(Metatype):

    name = "list"

    def formatValues(self, n, field, value):
        items = dict()
        with _utils.suppress(KeyError, warn=False):
            if not isinstance(n, Node):
                raise KeyError
            field_name = field.getName()
            items = dict(count_list_values_for_all_content_children(n.id, field_name))

        value = value.split(";")

        for val in field.getValueList():
            indent = len(val)-len(val.lstrip("*"))
            indentstr = 2 * max(0, indent-1) * "&nbsp;"
            val = val.lstrip("*")
            selectable = (not indent) or val.startswith(" ")
            val = esc(val.strip())

            num = int(items.get(val, 0))
            if num<0:
                logg.error("num<0, using empty string")
            else:
                num = u" ({})".format(unicode(num)) if num else u""

            if not selectable:
                yield ("optgroup", '<optgroup label="{}{}">'.format(indentstr,val), "", "")
            elif val in value:
                yield ("optionselected", indentstr, val, num)
            else:
                yield ("option", indentstr, val, num)

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        context = Context(field, value=value, width=width, name=field.getName(), lock=lock, language=language)
        return tal.getTAL("metadata/list.html", {"context": context,
                                                 "valuelist": self.formatValues(None, field, value),
                                                 "required": 1 if required else None,
                                                 },
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/list.html",
                          {"context": context,
                           "valuelist": self.formatValues(context.collection, context.field, context.value),
                          },
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
            macro="metafieldeditor",
            language=language,
        )


    translation_labels = dict(
        de=dict(
            list_multiple="Mehrfachauswahl:",
            list_list_values="Listenwerte:",
            fieldtype_list="Werteliste",
            fieldtype_list_desc="Werte-Auswahlfeld als Drop-Down Liste",
        ),
        en=dict(
            list_multiple="Multiple choice:",
            list_list_values="List values:",
            fieldtype_list="valuelist",
            fieldtype_list_desc="drop down valuelist",
        ),
    )
