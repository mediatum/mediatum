# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Peter Heckl <heckl@ub.tum.de>

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
from __future__ import division
from __future__ import print_function

import logging
from collections import OrderedDict

from mediatumtal import tal

import core.translation as _core_translation
from core import config
from core import httpstatus
from core.metatype import Metatype
from core.translation import getDefaultLanguage

import re

logg = logging.getLogger(__name__)

max_lang_length = max([len(lang) for lang in config.languages])
config_default_language = getDefaultLanguage()


class m_htmlmemo(Metatype):

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
            "ident": ustr(field.id),
            "required": self.is_required(required)
        }

        s = tal.getTAL("metadata/htmlmemo.html", context, macro="editorfield", language=language)
        return s.replace("REPLACE_WITH_IDENT", unicode(field.id))

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/htmlmemo.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        return (metafield.getLabel(), value)

    def get_metafieldeditor_html(self, field, metadatatype, language):
        return tal.getTAL("metadata/htmlmemo.html", dict(value=field.getValues()), macro="maskeditor", language=language)

    def getPopup(self, req):
        assert req.values["type"] == "configfile"
        req.response.set_data(tal.processTAL(
                dict(lang=_core_translation.lang(req)),
                file="metadata/htmlmemo.html",
                macro="ckconfig",
                request=req,
            ))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK

    def getName(self):
        return "fieldtype_htmlmemo"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    # method for additional keys of type memo
    def getLabels(self):
        return m_htmlmemo.labels

    labels = {"de":
              [
                  ("editor_memo_label", u"Zeichen übrig"),
                  ("mask_edit_max_length", u"Maximallänge"),
                  ("fieldtype_htmlmemo", "HTML Memofeld"),
                  ("fieldtype_htmlmemo_desc", u"Memofeld mit HTML Markup"),
                  ("htmlmemo_titlepopupbutton", u"Editiermaske öffnen"),
                  ("htmlmemo_popup_title", u"Eingabemaske für HTML formatierte Texte"),
                  ("htmlmemo_valuelabel", "Wert:"),
              ],
              "en":
              [
                  ("editor_htmlmemo_label", "characters remaining"),
                  ("mask_edit_max_length", "Max. length"),
                  ("fieldtype_htmlmemo", "html memo"),
                  ("fieldtype_htmlmemo_desc", "memo field with html markup"),
                  ("htmlmemo_titlepopupbutton", "open editor mask"),
                  ("htmlmemo_popup_title", "Editor mask for HTML formatted text"),
                  ("htmlmemo_valuelabel", "Value:"),
              ]
              }
