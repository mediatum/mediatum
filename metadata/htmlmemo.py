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
from core.metatype import Metatype

import re

logg = logging.getLogger(__name__)

max_lang_length = max([len(lang) for lang in config.languages])


class m_htmlmemo(Metatype):

    name = "htmlmemo"

    default_settings = dict(
        max_length=None,
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
            dict(value=fielddata["max_length"]),
            macro="metafieldeditor",
            language=language,
        )

    def parse_metafieldeditor_settings(self, data):
        return dict(
            max_length=int(data["max_length"]) if data["max_length"] else None,
        )

    def getPopup(self, req):
        assert req.values["type"] == "configfile"
        req.response.set_data(tal.processTAL(
                dict(lang=_core_translation.set_language(req.accept_languages)),
                file="metadata/htmlmemo.html",
                macro="ckconfig",
                request=req,
            ))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK


    translation_labels = dict(
        de=dict(
            editor_memo_label=u"Zeichen übrig",
            mask_edit_max_length=u"Maximallänge",
            fieldtype_htmlmemo="HTML Memofeld",
            fieldtype_htmlmemo_desc=u"Memofeld mit HTML Markup",
            htmlmemo_titlepopupbutton=u"Editiermaske öffnen",
            htmlmemo_popup_title=u"Eingabemaske für HTML formatierte Texte",
            htmlmemo_valuelabel="Wert:",
        ),
        en=dict(
            editor_htmlmemo_label="characters remaining",
            mask_edit_max_length="Max. length",
            fieldtype_htmlmemo="html memo",
            fieldtype_htmlmemo_desc="memo field with html markup",
            htmlmemo_titlepopupbutton="open editor mask",
            htmlmemo_popup_title="Editor mask for HTML formatted text",
            htmlmemo_valuelabel="Value:",
        ),
    )
