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
import utils.utils as _utils
from utils.utils import esc
from core.metatype import Metatype
import metadata.common_list as _common_list


logg = logging.getLogger(__name__)

q = db.query


def _format_elements(field, *args):
    return _common_list.format_elements(field.getValueList(), field, *args)


class m_mlist(Metatype):

    name = "mlist"

    def get_default_value(self, field):
        valuelist = next(_format_elements(field))
        if valuelist.opt in ("option", "optionselected"):
            return valuelist.item

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/mlist.html",
                          dict(
                              lock=lock,
                              name=field.getName(),
                              required=1 if required else None,
                              valuelist=_format_elements(field, value.split(";")),
                              width=width,
                          ),
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL("metadata/mlist.html",
                          dict(
                              name=name,
                              value=value,
                              valuelist=_format_elements(field, value, collection),
                          ),
                          macro="searchfield",
                          language=language)

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
