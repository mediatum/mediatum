# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from mediatumtal import tal
from core.metatype import Metatype
from core import Node
from lib.iptc.IPTC import get_wanted_iptc_tags
logg = logging.getLogger(__name__)


class m_meta(Metatype):

    name = "meta"

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL("metadata/meta.html", {"lock": lock,
                                                 "value": value,
                                                 "width": width,
                                                 "name": field.getName(),
                                                 "field": field},
                          macro="editorfield",
                          language=language)

    def getSearchHTML(self, context):
        return tal.getTAL("metadata/meta.html", {"context": context}, macro="searchfield", language=context.language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        return (metafield.getLabel(), node.get(metafield.getValues()))

    def get_metafieldeditor_html(self, field, metadatatype, language):
        value = field.getValues().split("\r\n")
        value.extend(("",)*2)
        value = value[:2]

        attr = {}
        if metadatatype:
            for t in metadatatype.getDatatypes():
                content_class = Node.get_class_for_typestring(t)
                node = content_class(name=u'')
                try:
                    attr.update(node.getTechnAttributes())
                    attr['IPTC'] = get_wanted_iptc_tags()
                except AttributeError:
                    logg.exception("attribute error in get_metafieldeditor_html, continue")
                    continue

        return tal.getTAL("metadata/meta.html", {"value": value, "t_attrs": attr}, macro="metafieldeditor", language=language)


    translation_labels = dict(
        de=dict(
            metafield_tech_meta="Technisches Metadatenfeld:",
            metafield_metadata_field="Metadatenfeld",
            fieldtype_meta="Technisches Metadatum",
            fieldtype_meta_desc="Technisches Metadatum (automatisch vom System erstellt)",
        ),
        en=dict(
            metafield_tech_meta="Technical metadata field:",
            fieldtype_meta="technical metadata",
            fieldtype_meta_desc="field for technical metadata (automatically filled in by mediatum)",
        ),
    )
