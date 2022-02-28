# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from collections import OrderedDict
from mediatumtal import tal

import core.translation as _core_translation
from core import config
from core import httpstatus
from core.metatype import Metatype, charmap

import re

logg = logging.getLogger(__name__)

max_lang_length = max([len(lang) for lang in config.languages])


class m_memo(Metatype):

    name = "memo"

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):

        try:
            field_node_name = field.name
        except:
            field_node_name = None

        context = {
            "lock": lock,
            "value": value,
            "width": width,
            "name": field_node_name,
            "field": field,
            "t": _core_translation.t,
            "ident": ustr(field.id),
            "required": 1 if required else None,
        }

        return tal.getTAL("metadata/memo.html",
                          context,
                          macro="editorfield")

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/memo.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        return (metafield.getLabel(), value)

    def get_metafieldeditor_html(self, field, metadatatype, language):
        return tal.getTAL(
            "metadata/memo.html",
            dict(value=field.getValues()),
            macro="maskeditor",
            language=language,
        )


    # method for popup methods of type memo
    def getPopup(self, req):
        req.response.set_data(tal.processTAL(
                dict(charmap=charmap, name=req.values.get("name"), value=req.values.get("value")),
                file="metadata/memo.html",
                macro="popup",
                request=req,
            ))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK

    translation_labels = dict(
        de=dict(
            editor_memo_label=u"Zeichen übrig",
            mask_edit_max_length=u"Maximallänge",
            fieldtype_memo="Memofeld",
            fieldtype_memo_desc=u"Texteingabefeld beliebiger Länge",
            memo_titlepopupbutton=u"Editiermaske öffnen",
            memo_popup_title=u"Eingabemaske für Sonderzeichen",
            memo_valuelabel="Wert:",
            memo_formatedvalue="Formatierter Wert:",
            memo_done=u"Übernehmen",
            memo_cancel="Abbrechen",
            memo_spcchar="Sonderzeichen:",
            memo_bold_title="Markierten Text 'Fett' setzen",
            memo_italic_title="Markierten Text 'Kursiv' setzen",
            memo_sub_title="Markierten Text 'tiefstellen'",
            memo_sup_title="Markierten Text 'hochstellen'",
        ),
        en=dict(
            editor_memo_label="characters remaining",
            mask_edit_max_length="Max. length",
            fieldtype_memo="memo",
            fieldtype_memo_desc="textfield for any text length",
            memo_titlepopupbutton="open editor mask",
            memo_popup_title="Editor mask for specialchars",
            memo_valuelabel="Value:",
            memo_formatedvalue="Formated Value:",
            memo_done="Done",
            memo_cancel="Cancel",
            memo_spcchar="Special chars:",
            memo_bold_title="set marked text 'bold'",
            memo_italic_title="set marked text 'italic'",
            memo_sub_title="set marked text 'subscript'",
            memo_sup_title="set marked text 'superscript'",
        ),
    )
