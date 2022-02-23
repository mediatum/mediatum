# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
from core.metatype import Metatype


class m_check(Metatype):

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/check.html", {"lock": lock,
                                                  "value": value,
                                                  "width": width,
                                                  "name": field.getName(),
                                                  "field": field,
                                                  "required": 1 if required else None,
                                                  },
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/check.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.name)
        return (metafield.label, value)

    translation_labels = dict(
        de=dict(
            fieldtype_check="Checkbox",
            fieldtype_check_desc=u"Checkbox Auswahl (für Ja/Nein-Werte)",
        ),
        en=dict(
            fieldtype_check="checkbox",
            fieldtype_check_desc="checkbox field (true/false)",
        ),
    )
