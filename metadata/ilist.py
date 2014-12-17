"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Peter Heckl <heckl@ub.tum.de>

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
from mediatumtal import tal
#import core.search as search
import core.tree as tree
from utils.utils import esc
from core.metatype import Metatype
from core.acl import AccessData
from core.transition import httpstatus


logg = logging.getLogger("frontend")


class m_ilist(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None):
        return tal.getTAL("metadata/ilist.html", {"lock": lock, "value": value, "width": width,
                                                  "name": field.getName(), "field": field}, macro="editorfield", language=language)

    def getSearchHTML(self, context):
        n = context.collection
        valuelist = n.getAllAttributeValues(context.field.getName(), context.access)
        keys = sorted(valuelist.keys())
        v = []
        for key in keys:
            v.append((key, valuelist[key]))
        return tal.getTAL("metadata/ilist.html", {"context": context, "valuelist": v}, macro="searchfield", language=context.language)

    def getFormatedValue(self, field, node, language=None, html=1):
        value = node.get(field.getName())
        try:
            if value[-1] == ";":
                value = value[0:-1]
        except:
            pass

        value = value.replace(";", "; ")
        if html:
            value = esc(value)
        return (field.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        #value = value.replace(", ",";")
        return value

    def getName(self):
        return "fieldtype_ilist"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    def getPopup(self, req):
        access = AccessData(req)
        try:
            name = req.params['name']
            fieldname = req.params.get('fieldname', name)
        except:
            logg.exception("missing request parameter")
            return httpstatus.HTTP_NOT_FOUND

        index = tree.getRoot("collections").getAllAttributeValues(name, access, req.params.get('schema')).keys()
        index.sort(lambda x, y: cmp(x.lower(), y.lower()))

        if req.params.get("print", "") != "":
            req.reply_headers["Content-Disposition"] = "attachment; filename=index.txt"
            for word in index:
                if word.strip() != "":
                    req.write(word.strip() + "\r\n")
            return

        req.writeTAL("metadata/ilist.html", {"index": index, "fieldname": fieldname}, macro="popup")
        return httpstatus.HTTP_OK

    # method for additional keys of type spctext
    def getLabels(self):
        return m_ilist.labels

    labels = {"de":
              [
                  ("editor_index", "Index"),
                  ("editor_index_title", "Indexwerte anzeigen"),
                  ("popup_index_header", "Vorhandene Indexwerte"),
                  ("popup_indexnumber", "Wert(e) selektiert"),
                  ("popup_listvalue_title", "Listenwerte als Popup anzeigen"),
                  ("popup_listvalue", "Listenwerte anzeigen"),
                  ("popup_clearselection_title", "Auswahlliste leeren"),
                  ("popup_clearselection", "Auwahl aufheben"),
                  ("popup_ok", "OK"),
                  ("popup_cancel", "Abbrechen"),
                  ("fieldtype_ilist", "Werteliste mit Index"),
                  ("fieldtype_ilist_desc", "Eingabefeld mit Index als Popup"),
                  ("ilist_titlepopupbutton", "Editiermaske \xc3\xb6ffnen")
              ],
              "en":
              [
                  ("editor_index", "Index"),
                  ("editor_index_title", "show index values"),
                  ("popup_index_header", "Existing Index values"),
                  ("popup_ok", "OK"),
                  ("popup_cancel", "Cancel"),
                  ("popup_listvalue_title", "Show list values as popup"),
                  ("popup_listvalue", "show list values"),
                  ("popup_clearselection", "clear selection"),
                  ("popup_clearselection_title", "Unselect all values"),
                  ("popup_indexnumber", "values selected"),
                  ("fieldtype_ilist", "indexlist"),
                  ("fieldtype_ilist_desc", "input field with index"),
                  ("ilist_titlepopupbutton", "open editor mask")
              ]
              }
