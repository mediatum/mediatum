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
from mediatumtal import tal
import logging
import re
from core.metatype import Metatype
from core.translation import t
from urllib import unquote
from utils.utils import quote_uri


logg = logging.getLogger("frontend")


def _replace_vars(node, s):
    for var in re.findall(r'<(.+?)>', s):
        if var == "att:id":
            s = s.replace("<" + var + ">", node.id)
        elif var.startswith("att:"):
            val = node.get(var[4:])
            if val == "":
                val = "____"
            s = s.replace("<" + var + ">", val)

    for var in re.findall(r'\[(.+?)\]', s):
        if var == "att:id":
            s = s.replace("[" + var + "]", node.id)
        elif var.startswith("att:"):
            val = node.get(var[4:])
            if val == "":
                val = "____"
            s = s.replace("[" + var + "]", val)
    return s


class m_url(Metatype):

    icons = {"externer Link": "/img/extlink.png", "Email": "/img/email.png"}
    targets = {"selbes Fenster": "same", "neues Fenster": "_blank"}

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        fielddef = field.getValues().split("\r\n")
        if len(fielddef) != 3:
            fielddef = ("", "", "")
        val = value.split(";")
        # XXX: ???
        if len(val) != 2:
            val = ("", "")

        return tal.getTAL("metadata/url.html", {"lock": lock,
                                                "value": val,
                                                "fielddef": fielddef,
                                                "width": width,
                                                "name": field.getName(),
                                                "field": field,
                                                "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getAdminFieldsHTML(self, values={}):
        return tal.getTAL("metadata/url.html",
                          {"valuelist": values["valuelist"],
                           "icons": m_url.icons,
                           "url_targets": m_url.targets},
                          macro="fieldeditor",
                          language=values["language"])

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/url.html", {"context": context}, macro="searchfield", language=context.language)

    #
    # format node value depending on field definition
    #
    def getFormatedValue(self, field, node, language=None, html=1):
        try:
            value = node.get(field.getName()).split(";")
            fielddef = field.getValues().split("\r\n")

            while len(fielddef) < 4:
                fielddef.append("")

            l = []
            for i in range(0, 4):
                try:
                    if value[i]:
                        l.append(value[i])
                    else:
                        l.append(fielddef[i])
                except:
                    l.append(fielddef[i])

            uri, linktext, icon, target = [_replace_vars(node, p) for p in l]

            # find unsatisfied variables
            if str(uri).find("____") >= 0:
                uri = ''
            if str(linktext).find("____") >= 0:
                linktext = ''

            if len(fielddef) < 4:
                target = ""
            if uri != "" and linktext == "":
                linktext = unquote(uri)

            if uri == '' and linktext == '':
                value = icon = ""
            # XXX: ???
            elif uri == '' and linktext != '':
                value = linktext
                icon = ""
            else:  # link and text given
                if target in ["", "_blank"]:
                    value = '<a href="{}" target="_blank" title="{}">{}</a>'.format(uri, t(language, 'show in new window'), linktext)
                else:
                    value = '<a href="{}">{}</a>'.format(uri, linktext)
            if icon != "":
                value += '<img src="{}"/>'.format(icon)

            return (field.getLabel(), value)
        except:
            logg.error("error getting formatted value for URI", exc_info=1)
            return (field.getLabel(), "")

    def format_request_value_for_db(self, field, params, item, language=None):
        uri = params.get(item)
        quoted_uri = quote_uri(uri)
        linktext = params.get(item + "_text").replace(";", "\xcd\xbe")
        if not quoted_uri:
            return ""
        return "{};{}".format(quoted_uri, linktext)

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        try:
            value = field.getValues().split("\r\n")
        except:
            value = []
        while len(value) < 4:
            value.append("")
        return tal.getTAL("metadata/url.html",
                          {"value": value,
                           "icons": m_url.icons,
                           "url_targets": m_url.targets},
                          macro="maskeditor",
                          language=language)

    def getName(self):
        return "fieldtype_url"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    # method for additional keys of type url
    def getLabels(self):
        return m_url.labels

    labels = {"de":
              [
                  ("url_edit_link", "Link:"),
                  ("url_edit_linktext", "Angezeigter Text:"),
                  ("url_edit_icon", "Icon:"),
                  ("url_edit_noicon", "-kein Icon-"),
                  ("url_edit_preview", "Vorschau:"),
                  ("url_urltarget", "Linkziel:"),
                  ("fieldtype_url", "URL"),
                  ("fieldtype_url_desc", "externer Link (neues Fenster)")

              ],
              "en":
              [
                  ("url_edit_link", "Link:"),
                  ("url_edit_linktext", "Link Text:"),
                  ("url_edit_icon", "Icon:"),
                  ("url_edit_noicon", "-kein Icon-"),
                  ("url_edit_preview", "Preview:"),
                  ("url_urltarget", "Link target:"),
                  ("fieldtype_url", "url"),
                  ("fieldtype_url_desc", "external link (new window)")

              ]
              }
