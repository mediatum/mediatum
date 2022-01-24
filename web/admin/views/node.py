# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer
import core.csrfform as _core_csrfform
from core import Node, File, db
from web.admin.views import BaseAdminView
from core.database.postgres.node import NodeAlias


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
    form_base_class = _core_csrfform.CSRFForm

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
    form_base_class = _core_csrfform.CSRFForm

    column_filters = ("path", "filetype", "mimetype")
    column_editable_list = ("path", "filetype", "mimetype")
    form_columns = ("nodes", "path", "filetype", "mimetype")
    form_ajax_refs = {
        "nodes": {"fields": (Node.name, )}
    }

    def __init__(self, session=db.session, *args, **kwargs):
        super(FileView, self).__init__(File, session, category="Node", *args, **kwargs)

class NodeAliasView(BaseAdminView):
    form_base_class = _core_csrfform.CSRFForm

    def __init__(self, session=db.session, *args, **kwargs):
        super(NodeAliasView, self).__init__(NodeAlias, session, category="Node", *args, **kwargs)

    form_columns = ("alias", "nid", "description")
    column_labels = {"nid": "Node ID"}
