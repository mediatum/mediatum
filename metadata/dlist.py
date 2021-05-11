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

import utils.utils as _utils
from utils.utils import esc, suppress
from core.metatype import Metatype
from core import Node
from core import db
from contenttypes import Home, Collections
from core.systemtypes import Root
import metadata.common_list as _common_list

q = db.query

logg = logging.getLogger(__name__)


def _download_list(metafield):
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

    metacfg = metafield.metatype_data
    with _contextlib.closing(urllib2.urlopen(metacfg["data_address"])) as data:
        if metacfg["data_type"]=="list":
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
        assert metacfg["data_type"]=="json"
        data = json.load(data)
    key_attr, key_value = metacfg["attribute"], metacfg["value"]
    data.sort(key=_operator.itemgetter(key_attr))
    for item in data:
        yield dict(
                select_text=metacfg["selection_format"].replace(key_attr, item[key_attr]).replace(key_value, item[key_value]),
                select_value=item[key_value],
               )


def _format_elements(node, field, value):
    return _common_list.format_elements(
        _itertools.imap(_operator.itemgetter("select_value"), _download_list(field)),
        field,
        value.split(";"),
        node,
       )


class m_dlist(Metatype):

    name = "dlist"

    default_settings = dict(
        data_address="",
        data_type="",
        attribute="",
        value="",
        selection_format="",
    )

    def get_default_value(self, field):
        element = next(_format_elements(None, field, ""))
        if element.opt in ("option", "optionselected"):
            return element.item

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None, required=None):
        valuelist = []
        with suppress(ValueError, warn=False):
            valuelist = list(_download_list(field))

        if name == "":
            name = field.getName()
        return tal.getTAL(
                "metadata/dlist.html",
                dict(
                    lock=lock,
                    name=name,
                    width=width,
                    value=value,
                    valuelist=valuelist,
                    required=1 if required else None,
                  ),
                macro="editorfield",
                language=language,
               )


    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/dlist.html",
                dict(
                    name=name,
                    value=value,
                    valuelist=_format_elements(collection, field, value),
                   ),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def get_metafieldeditor_html(self, fielddata, metadatatype, language):
        return tal.getTAL(
            "metadata/dlist.html",
            dict(
                data_address=fielddata["data_address"],
                data_type=fielddata["data_type"],
                attribute=fielddata["attribute"],
                value=fielddata["value"],
                selection_format=fielddata["selection_format"],
                types=['json', 'list'],
            ),
            macro="metafieldeditor",
            language=language,
        )

    def parse_metafieldeditor_settings(self, data):
        return dict(
            data_address=data["data_address"],
            data_type=data["data_type"],
            attribute=data["attribute"],
            value=data["value"],
            selection_format=data["selection_format"],
        )

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
