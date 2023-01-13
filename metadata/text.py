# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import re
from mediatumtal import tal
from core import httpstatus
import core.config as config
from utils.utils import esc
from utils.utils import modify_tex
import core.metatype as _core_metatype
from core.metatype import Metatype
from utils.strings import replace_attribute_variables
from web import frontend as _web_frontend

logg = logging.getLogger(__name__)


class m_text(Metatype):

    name = "text"

    def editor_get_html_form(self, metafield, metafield_name_for_html, values, required, language):

        conflict = len(frozenset(values))!=1

        return _core_metatype.EditorHTMLForm(tal.getTAL(
                "metadata/text.html",
                dict(
                    value="" if conflict else values[0],
                    name=metafield_name_for_html,
                    required=1 if required else None,
                   ),
                macro="editorfield",
                language=language,
                ), conflict)

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/text.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True, template_from_caller=None):

        value = node.get_special(metafield.name)
        # consider int, long values like filesize
        if isinstance(value, (int, long)):
            value = str(value)
        value = value.replace(";", "; ")

        # ignore trailing newlines for textfields
        value = value.rstrip("\r\n")

        if html:
            value = esc(value)

        # replace variables
        # substitute TeX sub/super-scripts with <sub>/<sup> html tags
        value = modify_tex(value, 'html')

        value = replace_attribute_variables(value, node.id, node.get, r'&lt;(.+?)&gt;', "&lt;", "&gt;")
        value = value.replace("&lt;", "<").replace("&gt;", ">")

        if not maskitem:
            return (metafield.getLabel(), value)

        # use default value from mask if value is empty
        if value == u'':
            value = maskitem.getDefault()

        return (metafield.getLabel(), value)

    def editor_parse_form_data(self, field, data):
        return data.get("text")
