# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
from utils.utils import esc
import core.metatype as _core_metatype
from core.metatype import Metatype


class m_number(Metatype):

    name = "number"

    def editor_get_html_form(self, metafield, metafield_name_for_html, values, required, language):

        conflict = len(frozenset(values))!=1

        return _core_metatype.EditorHTMLForm(tal.getTAL(
                "metadata/number.html",
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
                "metadata/number.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def editor_parse_form_data(self, field, data):
        return data.get("number")
