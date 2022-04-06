# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import functools as _functools
import itertools as _itertools
import logging
import operator as _operator
import locale
import html as _html
import backports.functools_lru_cache as _backports_functools_lru_cache
from sqlalchemy import func, sql
from mediatumtal import tal

from utils.utils import esc, suppress
from core.metatype import Metatype
from core import httpstatus
from core import db
from core import Node
from contenttypes import Collections
from web.edit.modules.manageindex import getAllAttributeValues
from core.database.postgres import mediatumfunc
from core.database.postgres.alchemyext import exec_sqlfunc
import metadata.common_list as _common_list

q = db.query
logg = logging.getLogger(__name__)


def _get_list_values_for_nodes_with_schema(schema, attribute_name):
    res = q(Node.attrs[attribute_name]).filter_read_access()
    # here we have filtered out node without access rights
    res = res.filter(Node.schema == schema)
    # here we have picked all nodes with the correct schema
    res = _itertools.chain.from_iterable(res.yield_per(2**14))
    res = _itertools.ifilter(None, res)
    res = _itertools.imap(_operator.methodcaller("split", ";"), res)  # ( ("item1","item2"), ("item3","item4"), ...)
    res = _itertools.chain.from_iterable(res)  # ( "item1", "item2", "item3", "item4", ...)
    res = _itertools.imap(_operator.methodcaller("strip"), res)
    res = _itertools.ifilter(None, res)
    return frozenset(res)


class m_ilist(Metatype):

    name = "ilist"

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/ilist.html", {"lock": lock,
                                                  "value": value,
                                                  "width": width,
                                                  "name": field.getName(),
                                                  "field": field,
                                                  "required": 1 if required else None,
                                                  },
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, collection, field, language, name, value):
        # `value_and_count` contains a list of options,
        # each option is represented by a tuple of its name and its count.
        value_and_count = _common_list.count_list_values_for_all_content_children(collection.id,
                                                                                  field.getName())

        # We build three iterators here:
        # `value` contains all option names, properly escaped for HTML.
        # `count` contains the respective count of each option (i.e. its number of occurrences).
        # `ifselected` contains (in the end) empty strings for each option,
        #     but the special string 'selected="selected"' for the one and only selected option.
        #     It is constructed by comparing each value name with the context value
        #     (this leads to many "False" values and one "True" value),
        #     then turning the result into an int (that is 0 or 1),
        #     then multiplying the int with the special string.
        # Note: tee created three iterators that all contain the entries of `value_and_count`.
        ifselected, value, count = _itertools.tee(value_and_count, 3)
        count = _itertools.imap(_operator.itemgetter(1), count)
        value = _itertools.imap(_operator.itemgetter(0), value)
        value = _itertools.imap(_html.escape, value)
        ifselected = _itertools.imap(_operator.itemgetter(0), ifselected)
        ifselected = _itertools.imap(_functools.partial(_operator.eq, value), ifselected)
        ifselected = _itertools.imap(int, ifselected)
        ifselected = _itertools.imap(_functools.partial(_operator.mul, 'selected="selected" '), ifselected)

        # Now we apply all iterators to the format function
        # and create the long HTML option list.
        format_option = u'<option {0}value="{1}">{1} ({2})</option>\n'.format
        option_list = u"".join(_itertools.starmap(format_option, _itertools.izip(ifselected, value, count)))

        return tal.getTAL(
                "metadata/ilist.html",
                dict(name=name, option_list=option_list),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        with suppress(Exception):
            if value and value[-1] == ";":
                value = value[0:-1]

        value = value.replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def format_request_value_for_db(self, field, params, item, language=None):
        value = params.get(item)
        return value


    def getPopup(self, req):
        try:
            name = req.params['name']
            schema = req.args['schema']
            fieldname = req.params.get('fieldname', name)
        except:
            logg.exception("missing request parameter")
            req.response.status_code = httpstatus.HTTP_NOT_FOUND
            return httpstatus.HTTP_NOT_FOUND

        index = sorted(_get_list_values_for_nodes_with_schema(schema, fieldname))

        req.response.status_code = httpstatus.HTTP_OK
        if req.params.get("print", "") != "":
            req.response.headers["Content-Disposition"] = "attachment; filename=index.txt"
            req.response.set_data(u"".join(_itertools.imap(u"{}\r\n".format, index)))
            return

        option_list = _itertools.imap(_html.escape, index)
        option_list = u"".join(_itertools.imap(u"<option value=\"{0}\">{0}</option>\n".format, option_list))
        req.response.set_data(tal.processTAL({"option_list": option_list, "fieldname": fieldname, "schema": schema}, file="metadata/ilist.html", macro="popup", request=req))
        return httpstatus.HTTP_OK

    translation_labels = dict(
        de=dict(
            editor_index="Index",
            editor_index_title="Indexwerte anzeigen",
            popup_index_header="Vorhandene Indexwerte",
            popup_indexnumber="Wert(e) selektiert",
            popup_listvalue_title="Listenwerte als Popup anzeigen",
            popup_listvalue="Listenwerte anzeigen",
            popup_clearselection_title="Auswahlliste leeren",
            popup_clearselection="Auwahl aufheben",
            popup_ok="OK",
            popup_cancel="Abbrechen",
            fieldtype_ilist="Werteliste mit Index",
            fieldtype_ilist_desc="Eingabefeld mit Index als Popup",
            ilist_titlepopupbutton=u"Editiermaske öffnen",
        ),
        en=dict(
            editor_index="Index",
            editor_index_title="show index values",
            popup_index_header="Existing Index values",
            popup_ok="OK",
            popup_cancel="Cancel",
            popup_listvalue_title="Show list values as popup",
            popup_listvalue="show list values",
            popup_clearselection="clear selection",
            popup_clearselection_title="Unselect all values",
            popup_indexnumber="values selected",
            fieldtype_ilist="indexlist",
            fieldtype_ilist_desc="input field with index",
            ilist_titlepopupbutton="open editor mask",
        ),
    )
