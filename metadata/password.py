# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@ub.tum.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2010 Werner Neudenberger <neudenberger@ub.tum.de>

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
from core.transition import httpstatus
import re
from utils.utils import esc
from core.metatype import Metatype, charmap

import hashlib


class m_password(Metatype):

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        return tal.getTAL("metadata/password.html", {"lock": lock,
                                                     "value": value,
                                                     "width": width,
                                                     "name": field.getName(),
                                                     "field": field,
                                                     "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/password.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")

        if html:
            value = esc(value)

        # replace variables
        for var in re.findall(r'&lt;(.+?)&gt;', value):
            if var == "att:id":
                value = value.replace("&lt;" + var + "&gt;", unicode(node.id))
            elif var.startswith("att:"):
                val = node.get(var[4:])
                if val == "":
                    val = "____"

                value = value.replace("&lt;" + var + "&gt;", val)
        value = value.replace("&lt;", "<").replace("&gt;", ">")
        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        encrypted = hashlib.md5(value).hexdigest()
        if len(value) == 32:
            return value
        else:
            return encrypted

    def getName(self):
        return "fieldtype_password"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    # method for popup methods of type password
    def getPopup(self, req):
        req.writeTAL("metadata/password.html",
                     {"charmap": charmap, "name": req.params.get("name"), "value": req.params.get("value")}, macro="popup")
        return httpstatus.HTTP_OK

    # method for additional keys of type password
    def getLabels(self):
        return m_password.labels

    labels = {"de":
              [
                  ("password_popup_title", u"Eingabemaske für Passwort"),
                  ("fieldtype_password", "Passwortfeld"),
                  ("fieldtype_password_desc", "PasswordTexteingabefeld"),
                  ("password_titlepopupbutton", u"Editiermaske öffnen"),
                  ("password_valuelabel", "Wert:"),
                  ("password_done", u"Übernehmen"),
                  ("password_cancel", "Abbrechen"),
              ],
              "en":
              [
                  ("password_popup_title", "Editor mask for password"),
                  ("fieldtype_password", "password field"),
                  ("fieldtype_password_desc", "password text input field"),
                  ("password_titlepopupbutton", "open editor mask"),
                  ("password_valuelabel", "Value:"),
                  ("password_done", "Done"),
                  ("password_cancel", "Cancel"),
              ]
              }
