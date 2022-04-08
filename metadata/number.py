# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
from utils.utils import esc
from core.metatype import Metatype


class m_number(Metatype):

    name = "number"

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL(
                "metadata/number.html",
                dict(
                    lock=lock,
                    value=value,
                    width=width,
                    name=field.getName(),
                    field=field,
                    required=1 if required else None,
                   ),
                macro="editorfield",
                language=language
               )

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/number.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    translation_labels = dict(
        de=dict(
            fieldtype_number="Zahl",
            fieldtype_number_desc="Feld zur Eingabe eines Zahlenwertes",
        ),
        en=dict(
            fieldtype_number="number",
            fieldtype_number_desc="field for digit input",
        ),
    )
