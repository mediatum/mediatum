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
from core.transition import httpstatus
from core.metatype import Metatype, charmap
from core.translation import t, getDefaultLanguage

import re

logg = logging.getLogger(__name__)

max_lang_length = max([len(lang) for lang in config.languages])
config_default_language = getDefaultLanguage()


class m_memo(Metatype):

    additional_attrs = ['multilang']

    CUTTER_TEMPLATE = "---%s---"
    # CUTTER_PATTERN = re.compile(r"^---(?P<lang>\w{2,5})---$")
    CUTTER_PATTERN_STRING = (r"^%s$" % CUTTER_TEMPLATE) % ("(?P<lang>\w{2,%d})" % max_lang_length)
    CUTTER_PATTERN = re.compile(CUTTER_PATTERN_STRING, re.MULTILINE)
    DEFAULT_LANGUAGE_CUTTER = CUTTER_TEMPLATE % config_default_language

    def has_language_cutter(self, s):
        return bool(self.CUTTER_PATTERN.search(s))

    def language_snipper(self, s, language, joiner=""):
        lines = s.splitlines(True)
        res = []
        append_line = True
        for line in lines:
            m = self.CUTTER_PATTERN.match(line.strip())
            if not m:
                if append_line:
                    res.append(line)
            else:
                if m.groupdict()["lang"] == language:
                    res = []
                    append_line = True
                else:
                    append_line = False
        s = joiner.join(res)
        return s

    def str2dict(self, s, key_joiner="__", join_stringlists=True, only_config_langs=True):

        if not self.has_language_cutter(s):
            d = OrderedDict()

            for lang in config.languages:
                if lang == config_default_language:
                    d[lang] = s
                else:
                    d[lang] = ''

            return d

        lines = s.splitlines(True)

        d = OrderedDict()

        key = config_default_language
        key = "untagged"

        value = []
        d[key] = value
        append_line = True

        for line in lines:
            m = self.CUTTER_PATTERN.match(line)
            if not m:
                d[key].append(line)
            else:
                if d[key] and d[key][-1] and d[key][-1][-1] == '\n':
                    d[key][-1] = d[key][-1][0:-1]  # trailing \n belongs to found cutter
                key = m.groupdict()["lang"]
                if key in d:  # should not happen
                    logg.warn("----> default language conflict for: %s", key)
                    logg.warn("already in dict:d['%s'] = '%s'", key, d[key])
                value = []
                d[key] = value

        # handle unused languages
        keys = d.keys()
        for lang in config.languages:
            if lang not in keys:
                d[lang] = []

        # ignore keys not in languages
        if only_config_langs:
            keys = d.keys()
            for k in keys:
                if k not in config.languages:
                    del d[k]

        if join_stringlists:
            for k in d.keys():
                d[k] = ''.join(d[k])

        return d

    def language_update(self, old_str_all, new_str_lang, language, joiner="\n"):

        # set only_config_langs=True to delete not contigured langs when updating
        d = self.str2dict(old_str_all, join_stringlists=True, only_config_langs=True)

        d[language] = new_str_lang

        keys = d.keys()
        res_list = []
        for k in keys:
            val = d[k]
            res_list.append(self.CUTTER_TEMPLATE % k)  # how should empty values look like?
            if val:
                res_list.append(val)
        res_str = joiner.join(res_list)
        return res_str

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):

        # field may not be persisted as tree.Node and therefore may not have
        # an attribute "get"
        if hasattr(field, "get"):
            enable_multilang = bool(field.get('multilang'))
        else:
            enable_multilang = False

        if not language:
            language = getDefaultLanguage()

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
            "current_lang": language,
            "defaultlang": language,  # not the systems default language
            "languages": [],
            "langdict": {language: value},
            "language_snipper": self.language_snipper,
            "value_is_multilang": 'single',
            "multilang_display": 'display: none',
            "enable_multilang": enable_multilang,
            "expand_multilang": False,
            "required": self.is_required(required)
        }

        if enable_multilang:
            languages = config.languages
            lang = [l for l in languages if l != language]

            langdict = self.str2dict(value)
            context.update(
                {
                    "languages": lang,
                    "langdict": langdict,
                    "value_is_multilang": {True: 'multi', False: 'single'}[self.has_language_cutter(value)],
                    "multilang_display": {True: '', False: 'display: none'}[self.has_language_cutter(value)],
                })

            if enable_multilang and self.has_language_cutter(value):
                context["expand_multilang"] = True
            else:
                context["expand_multilang"] = False

        return tal.getTAL("metadata/memo.html",
                          context,
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/memo.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        value = self.language_snipper(value, language, joiner=u"\n")
        return (metafield.getLabel(), value)

    def getMaskEditorHTML(self, field, metadatatype=None, language=None, attr_dict={}):

        try:
            value = field.getValues()
        except AttributeError:
            value = u""

        context = {
            "value": value,
            "additional_attrs": ",".join(self.additional_attrs),
        }

        for attr_name in self.additional_attrs:
            context[attr_name] = ''

        context.update(attr_dict)

        return tal.getTAL("metadata/memo.html", context, macro="maskeditor", language=language)

    def getName(self):
        return "fieldtype_memo"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    # method for popup methods of type memo
    def getPopup(self, req):
        if "type" in req.params:
            if req.params.get('type') == 'javascript':
                req.reply_headers['Content-Type'] = "application/javascript"
                from core.translation import lang
                req.writeTAL("metadata/memo.html", {'lang': lang(req)}, macro="javascript")
        else:
            req.writeTAL(
                "metadata/memo.html", {"charmap": charmap, "name": req.params.get("name"), "value": req.params.get("value")}, macro="popup")
        return httpstatus.HTTP_OK

    # method for additional keys of type memo
    def getLabels(self):
        return m_memo.labels

    labels = {"de":
              [
                  ("editor_memo_label", u"Zeichen übrig"),
                  ("mask_edit_max_length", u"Maximallänge"),
                  ("mask_edit_enable_multilang", "Multilang aktivieren"),
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
                  ("memo_show_multilang", "umschalten zu mehrsprachig"),
                  ("memo_hide_multilang", "umschalten zu einsprachig"),


              ],
              "en":
              [
                  ("editor_memo_label", "characters remaining"),
                  ("mask_edit_max_length", "Max. length"),
                  ("mask_edit_enable_multilang", "activate multilang"),
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
                  ("memo_show_multilang", "switch to multilingual"),
                  ("memo_hide_multilang", "switch to monolingual"),
              ]
              }
