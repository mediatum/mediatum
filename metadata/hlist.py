# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import json
import operator

from mediatumtal import tal

import contenttypes.container as _contenttypes_container
from core.metatype import Metatype
from core import httpstatus
from core import Node
from core import db

q = db.query


class m_hlist(Metatype):

    name = "hlist"

    default_settings = dict(
        parentnode="",
        attrname="",
        onlylast=False,
    )

    def get_metafieldeditor_html(self, fielddata, metadatatype, language):
        return tal.getTAL(
            "metadata/hlist.html",
            dict(
                parentnode=fielddata.get("parentnode"),
                attrname=fielddata.get("attrname"),
                onlylast=fielddata.get("onlylast"),
            ),
            macro="metafieldeditor",
            language=language,
        )

    def parse_metafieldeditor_settings(self, data):
        assert data.get("onlylast") in (None, "1")
        return dict(
            parentnode=data["parentnode"],
            attrname=data["attrname"],
            onlylast=bool(data.get("onlylast")),
        )

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        metacfg = field.metatype_data
        return tal.getTAL(
                "metadata/hlist.html",
                dict(
                    lock=lock,
                    startnode=metacfg["parentnode"],
                    attrname=metacfg["attrname"],
                    onlylast=metacfg["onlylast"],
                    value=value,
                    width=width,
                    name=field.getName(),
                    field=field,
                    required=1 if required else None,
                   ),
                macro="editorfield",
                language=language,
               )

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = []
        ids = node.get(metafield.getName())
        if ids:
            for n in ids.split(';'):
                vn = q(Node).get(n)
                if vn is not None:
                    value.append(vn.getName())
        if metafield.metatype_data["onlylast"]:
            return metafield.getLabel(), value[-1]
        return metafield.getLabel(), u' - '.join(value)


    def getPopup(self, req):
        allowed_nodes = []
        attr_filter = req.args.get(u'attrfilter')
        attr_filter = operator.methodcaller("filter", Node.a[attr_filter] != '')

        # try direct container children
        children = []
        for nid in req.args.get(u'id').split(u'|'):
            node = q(Node).get(nid)
            if node.has_read_access():
                allowed_nodes.append(node)
                children.extend(attr_filter(node.children).filter_read_access())

        # if no direct children test all container children
        if not children:
            for node in allowed_nodes:
                children.extend(node.all_children_by_query(attr_filter(
                        q(_contenttypes_container.Container),
                    ).filter_read_access()))

        req.response.set_data(json.dumps({c.id: c.getName() for c in children}))
        req.response.status_code = httpstatus.HTTP_OK
        return httpstatus.HTTP_OK

    translation_labels = dict(
        de=dict(
            fieldtype_hlist="Hierarchische Werteliste",
            fieldtype_hlist_desc="Hierarchische Werteliste aus Attributwerten",
            hlist_edit_parentnodes="Basisknoten:",
            hlist_edit_attrname="Attributname:",
            hlist_edit_onlylast="Zeige nur Kindknoten:",
        ),
        en=dict(
            fieldtype_hlist="hierarchical list",
            fieldtype_hlist_desc="hierarchical list from attributes",
            hlist_edit_parentnodes="Base node:",
            hlist_edit_attrname="Attribute name:",
            hlist_edit_onlylast="Show only child:",
        ),
    )
