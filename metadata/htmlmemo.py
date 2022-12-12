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

    def editor_get_html_form(self, field, value="", width=400, lock=0, language=None, required=None):
        s = tal.getTAL(
                "metadata/htmlmemo.html",
                dict(
                    lock=lock,
                    value=value,
                    width=width,
                    name=field.name,
                    max_length=field.metatype_data['max_length'],
                    ident=ustr(field.id),
                    required=1 if required else None,
                    wysiwyg=field.metatype_data['wysiwyg'],
                   ),
                macro="editorfield",
                language=language,
               )
        return s.replace("REPLACE_WITH_IDENT", unicode(field.id))

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

    def getPopup(self, req):
        req.response.set_data(
                tal.processTAL(
                    dict(
                        charmap=_core_metatype.charmap,
                        name=req.params.get("name"),
                        value=req.params.get("value"),
                        html_head_style_src=_web_frontend.html_head_style_src,
                        html_head_javascript_src=_web_frontend.html_head_javascript_src,
                       ),
                    file="metadata/htmlmemo.html",
                    macro="popup",
                    request=req,
                   )
                )
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK
