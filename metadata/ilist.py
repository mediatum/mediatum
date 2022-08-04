# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import functools as _functools
import httplib as _httplib
import itertools as _itertools
import logging
import operator as _operator
import html as _html

from mediatumtal import tal

import core as _core
import utils.utils as _utils
from utils.utils import esc, suppress
import core.metatype as _core_metatype
from core.metatype import Metatype
from core.database.postgres.node import Node
import metadata.common_list as _common_list
import schema.schema as _schema
from web import frontend as _web_frontend

logg = logging.getLogger(__name__)


def _get_list_values_for_nodes_with_schema(schema, attribute_name):
    res = _core.db.query(Node.attrs[attribute_name]).filter_read_access()
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

    def editor_get_html_form(self, metafield, metafield_name_for_html, values, required, language):

        conflict = len(frozenset(values))!=1

        return _core_metatype.EditorHTMLForm(tal.getTAL(
                "metadata/ilist.html",
                dict(
                    value="" if conflict else values[0],
                    name=metafield_name_for_html,
                    required=1 if required else None,
                    metafield=metafield,
                   ),
                macro="editorfield",
                language=language,
                ), conflict)

    def search_get_html_form(self, collection, field, language, name, value):
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
                dict(
                    name=name,
                    option_list=option_list,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        with suppress(Exception):
            if value and value[-1] == ";":
                value = value[0:-1]

        value = value.replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def getPopup(self, req):
        try:
            name = req.params['name']
            schema = req.args['schema']
            fieldname = req.params.get('fieldname', name)
        except:
            logg.exception("missing request parameter")
            req.response.status_code = _httplib.NOT_FOUND
            return _httplib.NOT_FOUND

        index = sorted(_get_list_values_for_nodes_with_schema(schema, fieldname))

        req.response.status_code = _httplib.OK
        if req.params.get("print", "") != "":
            req.response.headers["Content-Disposition"] = "attachment; filename=index.txt"
            req.response.set_data(u"".join(_itertools.imap(u"{}\r\n".format, index)))
            return

        option_list = _itertools.imap(_html.escape, index)
        option_list = u"".join(_itertools.imap(u"<option value=\"{0}\">{0}</option>\n".format, option_list))
        req.response.set_data(
                tal.processTAL(
                    dict(
                        option_list=option_list,
                        fieldname=fieldname,
                        metafield_name_for_html=_schema.sanitize_metafield_name(fieldname),
                        schema=schema,
                        html_head_style_src=_web_frontend.html_head_style_src,
                        html_head_javascript_src=_web_frontend.html_head_javascript_src,
                       ),
                    file="metadata/ilist.html",
                    macro="popup",
                    request=req,
                   )
               )
        return _httplib.OK

    def editor_parse_form_data(self, field, data, required):
        if required and not data.get("text"):
            raise _core_metatype.MetatypeInvalidFormData("edit_mask_required")
        if _utils.xml_check_illegal_chars_or_null(data.get("text")):
            raise _core_metatype.MetatypeInvalidFormData("edit_mask_illegal_char")
        return data.get("text")
