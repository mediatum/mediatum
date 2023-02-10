# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
from mediatumtal import tal
import core.metatype as _core_metatype
from core.metatype import Metatype
from core.database.postgres.node import Node
from lib.iptc.IPTC import get_wanted_iptc_tags
logg = logging.getLogger(__name__)


class m_meta(Metatype):

    name = "meta"

    default_settings = dict(
        fieldname=u"",
        synchronize=False,
    )

    def editor_get_html_form(self, metafield, metafield_name_for_html, values, required, language):
        conflict = len(frozenset(values))!=1
        return _core_metatype.EditorHTMLForm(tal.getTAL(
                "metadata/meta.html",
                dict(
                    value="" if conflict else values[0],
                    name=metafield_name_for_html,
                    fieldname=metafield.metatype_data['fieldname'],
                   ),
                macro="editorfield",
                language=language,
               ), conflict)

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/meta.html",
                dict(
                    name=name,
                    value=value,
                    ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        return (metafield.getLabel(), node.get(metafield.metatype_data['fieldname']))

    def admin_settings_get_html_form(self, fielddata, metadatatype, language):
        attr = {}
        if metadatatype:
            for t in metadatatype.getDatatypes():
                content_class = Node.get_class_for_typestring(t)
                node = content_class(name=u'')
                try:
                    attr.update(node.getTechnAttributes())
                    attr['IPTC'] = get_wanted_iptc_tags()
                except AttributeError:
                    logg.exception("attribute error in admin_settings_get_html_form, continue")
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

    def admin_settings_parse_form_data(self, data):
        assert data.get("synchronize") in (None, "1")
        return dict(
            fieldname=data["fieldname"],
            synchronize=bool(data.get("synchronize")),
        )

    def editor_parse_form_data(self, field, data, required):
        if required and not data.get("meta"):
            raise _core_metatype.MetatypeInvalidFormData("edit_mask_required")
        return data.get("meta")
