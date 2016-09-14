# -*- coding: utf-8 -*-
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
import locale
from sqlalchemy import func, sql
from mediatumtal import tal
from utils.utils import esc
from core.metatype import Metatype
from core.transition import httpstatus
from core import db
from core import Node
from contenttypes import Collections
from web.edit.modules.manageindex import getAllAttributeValues
from core.database.postgres import mediatumfunc
from core.database.postgres.alchemyext import exec_sqlfunc
from utils.lrucache import lru_cache

q = db.query
logg = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def count_list_values_for_all_content_children(collection_id, attribute_name):
    func_call = mediatumfunc.count_list_values_for_all_content_children(collection_id, attribute_name)
    stmt = sql.select([sql.text("*")], from_obj=func_call)
    res = db.session.execute(stmt)
    return res.fetchall()


def get_list_values_for_nodes_with_schema(schema, attribute_name):
    # XXX: more abstraction needed...
    func_call = mediatumfunc.get_list_values_for_nodes_with_schema(schema, attribute_name)
    stmt = sql.select([sql.text("*")], from_obj=func_call)
    res = db.session.execute(stmt)
    return [t[0] for t in res.fetchall()]


class m_ilist(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/ilist.html", {"lock": lock,
                                                  "value": value,
                                                  "width": width,
                                                  "name": field.getName(),
                                                  "field": field,
                                                  "required": self.is_required(required)},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        field_name = context.field.getName()
        value_and_count = count_list_values_for_all_content_children(context.collection.id, field_name)

        return tal.getTAL("metadata/ilist.html", {"context": context, "valuelist": value_and_count},
                          macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        try:
            if value and value[-1] == ";":
                value = value[0:-1]
        except:
            logg.exception("exception in getFormattedValue, ignore")
            pass

        value = value.replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        return value

    def getName(self):
        return "fieldtype_ilist"

    def getInformation(self):
        return {"moduleversion": "1.1", "softwareversion": "1.1"}

    def getPopup(self, req):
        try:
            name = req.params['name']
            schema = req.args['schema']
            fieldname = req.params.get('fieldname', name)
        except:
            logg.exception("missing request parameter")
            return httpstatus.HTTP_NOT_FOUND

        index = get_list_values_for_nodes_with_schema(schema, fieldname)

        if req.params.get("print", "") != "":
            req.reply_headers["Content-Disposition"] = "attachment; filename=index.txt"
            for word in index:
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
                  ("ilist_titlepopupbutton", u"Editiermaske öffnen")
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
