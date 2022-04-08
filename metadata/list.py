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
from core.metatype import Metatype
from core import Node
from core import db
import metadata.common_list as _common_list

q = db.query
logg = logging.getLogger(__name__)


def _format_elements(field, *args):
    return _common_list.format_elements(field.getValueList(), field, *args)


class m_list(Metatype):

    name = "list"

    def get_default_value(self, field):
        valuelist = next(_format_elements(field))
        if valuelist.opt in ("option", "optionselected"):
            return valuelist.item

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL(
                "metadata/list.html",
                dict(
                    field=field,
                    lock=lock,
                    multiple=field.get('multiple'),
                    name=field.getName(),
                    required=1 if required else None,
                    valuelist=_format_elements(field, value.split(";")),
                    width=width,
                  ),
                macro="editorfield",
                language=language,
               )

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/list.html",
                dict(
                    name=name,
                    value=value,
                    valuelist=_format_elements(field, value, collection),
                   ),
                macro="searchfield",
                language=language,
               )

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
                dict(
                    value=field.getValues(),
                    multiple_list=field.get('multiple'),
                   ),
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
