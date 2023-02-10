# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from collections import OrderedDict

from mediatumtal import tal

from core import httpstatus
import core.metatype as _core_metatype
from web import frontend as _web_frontend
import re

logg = logging.getLogger(__name__)


class m_htmlmemo(_core_metatype.Metatype):

    name = "htmlmemo"

    default_settings = dict(
        max_length=None,
        wysiwyg=False,
    )

    def editor_get_html_form(self, metafield, metafield_name_for_html, values, required, language):

        conflict = len(frozenset(values))!=1

        return _core_metatype.EditorHTMLForm(tal.getTAL(
                "metadata/htmlmemo.html",
                dict(
                    value="" if conflict else values[0],
                    max_length=metafield.metatype_data['max_length'],
                    name=metafield_name_for_html,
                    required=1 if required else None,
                    wysiwyg=metafield.metatype_data['wysiwyg'],
                   ),
                macro="editorfield",
                language=language,
                ), conflict)

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/htmlmemo.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        return (metafield.getLabel(), value)

    def admin_settings_get_html_form(self, fielddata, metadatatype, language):
        return tal.getTAL(
            "metadata/htmlmemo.html",
            dict(value=fielddata["max_length"], wysiwyg=fielddata["wysiwyg"]),
            macro="metafieldeditor",
            language=language,
        )

    def admin_settings_parse_form_data(self, data):
        assert data.get("wysiwyg") in (None, "1")
        assert not data["max_length"] or int(data["max_length"]) >= 0
        return dict(
            max_length=int(data["max_length"]) if data["max_length"] else None,
            wysiwyg=bool(data.get("wysiwyg")),
        )

    def editor_parse_form_data(self, field, data, required):
        if required and not data.get("htmlmemo"):
            raise _core_metatype.MetatypeInvalidFormData("edit_mask_required")
        return data.get("htmlmemo")
