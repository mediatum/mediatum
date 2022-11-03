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
import core.metatype as _core_metatype
from core.metatype import Metatype

import re

logg = logging.getLogger(__name__)

max_lang_length = max([len(lang) for lang in config.languages])


class m_htmlmemo(Metatype):

    name = "htmlmemo"

    default_settings = dict(
        max_length=None,
        wysiwyg=False,
    )

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):

        try:
            field_node_name = field.name
        except:
            field_node_name = None

        s = tal.getTAL(
                "metadata/htmlmemo.html",
                dict(
                    lock=lock,
                    value=value,
                    width=width,
                    name=field_node_name,
                    max_length=field.metatype_data['max_length'] or -1,
                    ident=ustr(field.id),
                    required=1 if required else None,
                    wysiwyg=field.metatype_data['wysiwyg'],
                   ),
                macro="editorfield",
                language=language,
               )
        return s.replace("REPLACE_WITH_IDENT", unicode(field.id))

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/htmlmemo.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        return (metafield.getLabel(), value)

    def get_metafieldeditor_html(self, fielddata, metadatatype, language):
        return tal.getTAL(
            "metadata/htmlmemo.html",
            dict(value=fielddata["max_length"], wysiwyg=fielddata["wysiwyg"]),
            macro="metafieldeditor",
            language=language,
        )

    def parse_metafieldeditor_settings(self, data):
        assert data.get("wysiwyg") in (None, "1")
        return dict(
            max_length=int(data["max_length"]) if data["max_length"] else None,
            wysiwyg=bool(data.get("wysiwyg")),
        )

    def getPopup(self, req):
        if "type" in req.values:
            assert req.values["type"] == "configfile"
            req.response.set_data(tal.processTAL(
                    dict(lang=_core_translation.set_language(req.accept_languages)),
                    file="metadata/htmlmemo.html",
                    macro="ckconfig",
                    request=req,
                ))
        else:
            req.response.set_data(
                    tal.processTAL(
                        dict(
                            charmap=_core_metatype.charmap,
                            name=req.params.get("name"),
                            value=req.params.get("value"),
                           ),
                        file="metadata/htmlmemo.html",
                        macro="popup",
                        request=req,
                       )
                    )
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK


    translation_labels = dict(
        de=dict(
            editor_htmlmemo_label=u"Zeichen übrig",
            mask_edit_max_length=u"Maximallänge",
            fieldtype_htmlmemo="HTML Memofeld",
            fieldtype_htmlmemo_desc=u"Memofeld mit HTML Markup",
            htmlmemo_titlepopupbutton=u"Editiermaske öffnen",
            htmlmemo_popup_title=u"Eingabemaske für HTML formatierte Texte",
            htmlmemo_valuelabel="Wert:",
            htmlmemo_formatedvalue="Formatierter Wert:",
            htmlmemo_done=u"Übernehmen",
            htmlmemo_cancel="Abbrechen",
            htmlmemo_spcchar="Sonderzeichen:",
            htmlmemo_bold_title="Markierten Text 'Fett' setzen",
            htmlmemo_italic_title="Markierten Text 'Kursiv' setzen",
            htmlmemo_sub_title="Markierten Text 'tiefstellen'",
            htmlmemo_sup_title="Markierten Text 'hochstellen'",
        ),
        en=dict(
            editor_htmlmemo_label="characters remaining",
            mask_edit_max_length="Max. length",
            fieldtype_htmlmemo="html memo",
            fieldtype_htmlmemo_desc="memo field with html markup",
            htmlmemo_titlepopupbutton="open editor mask",
            htmlmemo_popup_title="Editor mask for HTML formatted text",
            htmlmemo_valuelabel="Value:",
            htmlmemo_formatedvalue="Formated Value:",
            htmlmemo_done="Done",
            htmlmemo_cancel="Cancel",
            htmlmemo_spcchar="Special chars:",
            htmlmemo_bold_title="set marked text 'bold'",
            htmlmemo_italic_title="set marked text 'italic'",
            htmlmemo_sub_title="set marked text 'subscript'",
            htmlmemo_sup_title="set marked text 'superscript'",
        ),
    )
