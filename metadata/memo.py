# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
from collections import OrderedDict
from mediatumtal import tal
from core import config
from core import httpstatus
from core.metatype import Metatype, charmap
from core.translation import t, getDefaultLanguage

import re

logg = logging.getLogger(__name__)

max_lang_length = max([len(lang) for lang in config.languages])
config_default_language = getDefaultLanguage()


class m_memo(Metatype):


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
            "t": t,
            "ident": ustr(field.id),
            "required": self.is_required(required)
        }

        return tal.getTAL("metadata/memo.html",
                          context,
                          macro="editorfield")

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/memo.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        return (metafield.getLabel(), value)

    def get_metafieldeditor_html(self, field, metadatatype=None, language=None):

        try:
            value = field.getValues()
        except AttributeError:
            value = u""

        context = {
            "value": value,
        }

        return tal.getTAL("metadata/memo.html", context, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_memo"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    # method for popup methods of type memo
    def getPopup(self, req):
        if "type" in req.params:
            if req.params.get('type') == 'javascript':
                req.response.content_type = "application/javascript"
                from core.translation import lang
                req.response.set_data(tal.processTAL({'lang': lang(req)}, file="metadata/memo.html", macro="javascript", request=req))
        else:
            req.response.set_data(tal.processTAL({"charmap": charmap, "name": req.params.get("name"), "value": req.params.get("value")},
                                                 file="metadata/memo.html", macro="popup", request=req))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK

    # method for additional keys of type memo
    def getLabels(self):
        return m_memo.labels

    labels = {"de":
              [
                  ("editor_memo_label", u"Zeichen übrig"),
                  ("mask_edit_max_length", u"Maximallänge"),
                  ("fieldtype_memo", "Memofeld"),
                  ("fieldtype_memo_desc", u"Texteingabefeld beliebiger Länge"),
                  ("memo_titlepopupbutton", u"Editiermaske öffnen"),
                  ("memo_popup_title", u"Eingabemaske für Sonderzeichen"),
                  ("memo_valuelabel", "Wert:"),
                  ("memo_formatedvalue", "Formatierter Wert:"),
                  ("memo_done", u"Übernehmen"),
                  ("memo_cancel", "Abbrechen"),
                  ("memo_spcchar", "Sonderzeichen:"),
                  ("memo_bold_title", "Markierten Text 'Fett' setzen"),
                  ("memo_italic_title", "Markierten Text 'Kursiv' setzen"),
                  ("memo_sub_title", "Markierten Text 'tiefstellen'"),
                  ("memo_sup_title", "Markierten Text 'hochstellen'"),


              ],
              "en":
              [
                  ("editor_memo_label", "characters remaining"),
                  ("mask_edit_max_length", "Max. length"),
                  ("fieldtype_memo", "memo"),
                  ("fieldtype_memo_desc", "textfield for any text length"),
                  ("memo_titlepopupbutton", "open editor mask"),
                  ("memo_popup_title", "Editor mask for specialchars"),
                  ("memo_valuelabel", "Value:"),
                  ("memo_formatedvalue", "Formated Value:"),
                  ("memo_done", "Done"),
                  ("memo_cancel", "Cancel"),
                  ("memo_spcchar", "Special chars:"),
                  ("memo_bold_title", "set marked text 'bold'"),
                  ("memo_italic_title", "set marked text 'italic'"),
                  ("memo_sub_title", "set marked text 'subscript'"),
                  ("memo_sup_title", "set marked text 'superscript'"),
              ]
              }
