# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2013 Iryna Feuerstein <feuersti@in.tum.de>

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
import re
from mediatumtal import tal
from core.transition import httpstatus
import core.config as config
from utils.utils import esc
from utils.utils import modify_tex
from core.metatype import Metatype, charmap


logg = logging.getLogger(__name__)


class m_text(Metatype):

    def language_snipper(self, s, language, joiner="\n"):

        if s.find(joiner) <= 0:
            return s

        valueList = s.split(joiner)

        # copied from self.getEditorHTML
        lang2value = dict()
        i = 0
        while i + 1 < len(valueList):
            lang2value[valueList[i]] = valueList[i + 1]
            i = i + 2

        return lang2value.get(language, '')

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        lang = None
        languages = config.languages
        if language is None:
            language = languages[0]
        if field.getValues() and "multilingual" in field.getValues():
            lang = [l.strip() for l in languages if (l != language)]
        valueList = value.split("\n")
        values = dict()
        i = 0
        while i + 1 < len(valueList):
            values[valueList[i] + "__" + field.getName()] = valueList[i + 1]
            i = i + 2

        if language:
            defaultlang = language
        elif lang:
            defaultlang = lang[0]
        else:
            defaultlang = ""

        try:
            field_node_name = field.name
        except:
            field_node_name = None

        context = {
            "lock": lock,
            "values": values,
            "value": value,
            "width": width,
            "name": field_node_name,
            "field": field,
            "ident": field.id if field.id else "",
            "languages": lang,
            "defaultlang": defaultlang,
            "expand_multilang": True if value.find('\n') != -1 else False,
            "required": self.is_required(required),
            "required_multilang": True if value.find('\n') != -1 and self.is_required(required) else None,
        }
        return tal.getTAL("metadata/text.html", context, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/text.html", {"context": context}, macro="searchfield", language=context.language)

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            multilingual = field.getValues()
        except AttributeError:
            multilingual = u""
        return tal.getTAL("metadata/text.html", {"multilingual": multilingual}, macro="maskeditor", language=language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True, template_from_caller=None):

        value = node.get_special(metafield.name)
        # consider int, long values like filesize
        if isinstance(value, (int, long)):
            value = str(value)
        value = value.replace(";", "; ")

        # ignore trailing newlines for textfields
        value = value.rstrip("\r\n")

        if value.find('\n') != -1:
            valuesList = value.split('\n')
            if any(lang in valuesList for lang in config.languages):  # treat as multilingual
                index = 0
                try:
                    index = valuesList.index(language)
                    value = valuesList[index + 1]
                except ValueError as e:
                    msg = "Exception in getFormattedValue for textfield:\n"
                    msg += " valuesList=%r\n" % valuesList
                    msg += " node.name=%r, node.id=%r, node.type=%r\n" % (node.name, node.id, node.type)
                    msg += " metafield.name=%r, metafield.id=%r, metafield.type=%r\n" % (metafield.name, metafield.id, metafield.type)
                    msg += " language=%r, mask=%r" % (language, mask)
                    logg.exception(msg)

                    value = u""
            else:
                # treat as monolingual
                pass

        if html:
            value = esc(value)

        # replace variables
        # substitute TeX sub/super-scripts with <sub>/<sup> html tags
        value = modify_tex(value, 'html')

        for var in re.findall(r'&lt;(.+?)&gt;', value):
            if var == "att:id":
                value = value.replace("&lt;" + var + "&gt;", unicode(node.id))
            elif var.startswith("att:"):
                val = node.get(var[4:])
                if val == "":
                    val = "____"

                value = value.replace("&lt;" + var + "&gt;", val)
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

    def getName(self):
        return "fieldtype_text"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    # method for popup methods of type text
    def getPopup(self, req):
        if "type" in req.params:
            req.writeTAL("metadata/text.html", {}, macro="javascript")
        else:
            req.writeTAL(
                "metadata/text.html", {"charmap": charmap, "name": req.params.get("name"), "value": req.params.get("value")}, macro="popup")
        return httpstatus.HTTP_OK

    # method for additional keys of type text
    def getLabels(self):
        return m_text.labels

    labels = {"de":
              [
                  ("text_popup_title", u"Eingabemaske für Sonderzeichen"),
                  ("fieldtype_text", "Textfeld"),
                  ("fieldtype_text_desc", "Normales Texteingabefeld"),
                  ("text_titlepopupbutton", u"Editiermaske öffnen"),
                  ("text_valuelabel", "Wert:"),
                  ("text_formatedvalue", "Formatierter Wert:"),
                  ("text_done", u"Übernehmen"),
                  ("text_cancel", "Abbrechen"),
                  ("text_spcchar", "Sonderzeichen:"),
                  ("text_bold_title", "Markierten Text 'Fett' setzen"),
                  ("text_italic_title", "Markierten Text 'Kursiv' setzen"),
                  ("text_sub_title", "Markierten Text 'tiefstellen'"),
                  ("text_sup_title", "Markierten Text 'hochstellen'"),
                  ("text_show_multilang", "umschalten zu mehrsprachig"),
                  ("text_hide_multilang", "umschalten zu einsprachig"),
                  ("text_multilingual", "Mehrsprachigkeit aktivieren")
              ],
              "en":
              [
                  ("text_popup_title", "Editor mask for specialchars"),
                  ("fieldtype_text", "text field"),
                  ("fieldtype_text_desc", "normal text input field"),
                  ("text_titlepopupbutton", "open editor mask"),
                  ("text_valuelabel", "Value:"),
                  ("text_formatedvalue", "Formated Value:"),
                  ("text_done", "Done"),
                  ("text_cancel", "Cancel"),
                  ("text_spcchar", "Special chars:"),
                  ("text_bold_title", "set marked text 'bold'"),
                  ("text_italic_title", "set marked text 'italic'"),
                  ("text_sub_title", "set marked text 'subscript'"),
                  ("text_sup_title", "set marked text 'superscript'"),
                  ("text_show_multilang", "switch to multilingual"),
                  ("text_hide_multilang", "switch to monolingual"),
                  ("text_multilingual", "Activate multilingual mode")
              ]
              }
