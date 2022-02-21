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

    def get_metafieldeditor_html(self, field, metadatatype, language):
        values = field.get("valuelist").split(u';')
        values.extend(("",)*3)
        values = values[:3]
        return tal.getTAL(
            "metadata/hlist.html",
            {"value": dict(parentnode=values[0], attrname=values[1], onlylast=values[2])},
            macro="maskeditor",
            language=language,
        )

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        try:
            values = field.get("valuelist").split(';')
        except AttributeError:
            values = field.split('\r\n')
        while len(values) < 3:
            values.append(u'')
        return tal.getTAL(
            "metadata/hlist.html",
            {
                "lock": lock,
                "startnode": values[0],
                "attrname": values[1],
                "onlylast": values[2],
                "value": value,
                "width": width,
                "name": field.getName(),
                "field": field,
                "required": 1 if required else None,
            },
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
        values = metafield.get("valuelist").split(';')
        while len(values) < 3:
            values.append(u'')
        if values[2] == '1':
            return metafield.getLabel(), value[-1]
        return metafield.getLabel(), u' - '.join(value)

    def getName(self):
        return "fieldtype_hlist"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

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
