# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import re
from mediatumtal import tal
from core import httpstatus
import core.config as config
from utils.utils import esc
from utils.utils import modify_tex
from core.metatype import Metatype, charmap
from utils.strings import replace_attribute_variables


logg = logging.getLogger(__name__)


class m_text(Metatype):

    name = "text"

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
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
            "ident": field.id if field.id else "",
            "required": 1 if required else None,
        }
        return tal.getTAL("metadata/text.html", context, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return tal.getTAL(
                "metadata/text.html",
                dict(name=context.name, value=context.value),
                macro="searchfield",
                language=context.language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True, template_from_caller=None):

        value = node.get_special(metafield.name)
        # consider int, long values like filesize
        if isinstance(value, (int, long)):
            value = str(value)
        value = value.replace(";", "; ")

        # ignore trailing newlines for textfields
        value = value.rstrip("\r\n")

        if html:
            value = esc(value)

        # replace variables
        # substitute TeX sub/super-scripts with <sub>/<sup> html tags
        value = modify_tex(value, 'html')

        value = replace_attribute_variables(value, node.id, node.get, r'&lt;(.+?)&gt;', "&lt;", "&gt;")
        value = value.replace("&lt;", "<").replace("&gt;", ">")

        if not maskitem:
            return (metafield.getLabel(), value)

        # use default value from mask if value is empty
        if value == u'':
            value = maskitem.getDefault()

        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item, '')
        try:
            return value.replace("; ", ";")
        except:
            logg.exception("exception in format_request_value_for_db, returning value")
            return value


    # method for popup methods of type text
    def getPopup(self, req):
        req.response.set_data(tal.processTAL(
                dict(charmap=charmap, name=req.values.get("name"), value=req.values.get("value")),
                file="metadata/text.html",
                macro="popup",
                request=req,
            ))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK

    translation_labels = dict(
        de=dict(
            text_popup_title=u"Eingabemaske für Sonderzeichen",
            fieldtype_text="Textfeld",
            fieldtype_text_desc="Normales Texteingabefeld",
            text_titlepopupbutton=u"Editiermaske öffnen",
            text_valuelabel="Wert:",
            text_formatedvalue="Formatierter Wert:",
            text_done=u"Übernehmen",
            text_cancel="Abbrechen",
            text_spcchar="Sonderzeichen:",
            text_bold_title="Markierten Text 'Fett' setzen",
            text_italic_title="Markierten Text 'Kursiv' setzen",
            text_sub_title="Markierten Text 'tiefstellen'",
            text_sup_title="Markierten Text 'hochstellen'",
        ),
        en=dict(
            text_popup_title="Editor mask for specialchars",
            fieldtype_text="text field",
            fieldtype_text_desc="normal text input field",
            text_titlepopupbutton="open editor mask",
            text_valuelabel="Value:",
            text_formatedvalue="Formated Value:",
            text_done="Done",
            text_cancel="Cancel",
            text_spcchar="Special chars:",
            text_bold_title="set marked text 'bold'",
            text_italic_title="set marked text 'italic'",
            text_sub_title="set marked text 'subscript'",
            text_sup_title="set marked text 'superscript'",
        ),
    )
