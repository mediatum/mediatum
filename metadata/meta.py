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

    default_settings = dict(
        fieldname=u"",
        synchronize=False,
    )

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL(
                "metadata/meta.html",
                dict(
                    lock=lock,
                    value=value,
                    width=width,
                    name=field.getName(),
                    fieldname=field.metatype_data['fieldname'],
                   ),
                macro="editorfield",
                language=language,
               )

    def getSearchHTML(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/meta.html",
                dict(
                    name=name,
                    value=value,
                    ),
                macro="searchfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        return (metafield.getLabel(), node.get(metafield.metatype_data['fieldname']))

    def get_metafieldeditor_html(self, fielddata, metadatatype, language):
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

        return tal.getTAL(
            "metadata/meta.html",
            dict(
                fieldname=fielddata["fieldname"],
                synchronize= fielddata["synchronize"],
                t_attrs=attr,
            ),
            macro="metafieldeditor",
            language=language,
        )

    def parse_metafieldeditor_settings(self, data):
        assert data.get("synchronize") in (None, "1")
        return dict(
            fieldname=data["fieldname"],
            synchronize=bool(data.get("synchronize")),
        )


    translation_labels = dict(
        de=dict(
            metafield_tech_meta="Technisches Metadatenfeld:",
            metafield_fieldname="Metadatenfeld",
            fieldtype_meta="Technisches Metadatum",
            fieldtype_meta_desc="Technisches Metadatum (automatisch vom System erstellt)",
        ),
        en=dict(
            metafield_tech_meta="Technical metadata field:",
            metafield_fieldname="metafield",
            fieldtype_meta="technical metadata",
            fieldtype_meta_desc="field for technical metadata (automatically filled in by mediatum)",
        ),
    )
