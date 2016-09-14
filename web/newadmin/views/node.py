# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import json
import logging
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer
from core import Node, File, db
from web.newadmin.views import BaseAdminView

logg = logging.getLogger(__name__)


def _format_as_json_html(data):
    pygments_style = "colorful"
    formatter = HtmlFormatter(style=pygments_style)
    lexer = JsonLexer()
    formatted = highlight(json.dumps(data, indent=2), lexer, formatter)

    return Markup(
        "<style>" +
        formatter.get_style_defs('.highlight') +
        "</style>" + formatted)


class NodeView(BaseAdminView):

    column_list = ("id", "name", "type", "schema", "orderpos")
    column_filters = ("name", "type", "schema")
    column_searchable_list = column_filters
    column_editable_list = ("name", "type", "schema")
    form_columns = ("name", "type", "schema", "orderpos")

    column_formatters = {
        "attrs": lambda v, c, m, p: _format_as_json_html(m.attrs),
        "system_attrs": lambda v, c, m, p: _format_as_json_html(m.system_attrs)
    }

    def __init__(self, session=db.session, *args, **kwargs):
        super(NodeView, self).__init__(Node, session, category="Node", *args, **kwargs)


class FileView(BaseAdminView):

    column_filters = ("path", "filetype", "mimetype")
    column_editable_list = ("path", "filetype", "mimetype")
    form_columns = ("nodes", "path", "filetype", "mimetype")
    form_ajax_refs = {
        "nodes": {"fields": (Node.name, )}
    }

    def __init__(self, session=db.session, *args, **kwargs):
        super(FileView, self).__init__(File, session, category="Node", *args, **kwargs)
