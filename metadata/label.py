# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from mediatumtal import tal
from schema.schema import VIEW_DATA_ONLY, VIEW_DEFAULT
from core.metatype import Metatype
from core.database.postgres.node import Node
from core import db
from utils.utils import esc

q = db.query

class m_label(Metatype):

    name = "label"

    def getFormHTML(self, field, nodes, req):
        return tal.processTAL(
                dict(
                    label=field.getLabel()
                   ),
                file="metadata/label.html",
                macro="get_form_html",
                request=req,
               )

    def getViewHTML(self, field, nodes, flags, language=None, template_from_caller=None, mask=None):
        if flags & VIEW_DATA_ONLY:
            return []
        elif flags & VIEW_DEFAULT:
            # default view
            return '<b>' + field.getLabel() + '</b><br/>'
        else:
            return '<br/>'

    def getMetaHTML(self, parent, index, sub=False, language=None, fieldlist={}):
        """ return formated row for metaeditor """
        item = parent.getChildren().sort_by_orderpos()[index]
        ret = ''
        if not sub:
            ret += '<div id="' + ustr(item.id) + '" class="mediatum-admin-maskedit-maskitem">'
        ret += '<b>' + ustr(item.getLabel()) + '</b>'

        if not sub:
            ret += '<div align="right" id="' + ustr(item.id) + \
                '_sub" style="display:none"><small style="color:silver">(' + (item.get("type")) + ')</small>'
            if index > 0:
                ret += '''
                    <input
                        type="image"
                        src="/static/img/uparrow.svg"
                        name="up_{}"
                        i18n:attributes="title mask_edit_up_title"
                        class="mediatum-icon-small"
                    />
                    '''.format(item.id)
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            if index < len(parent.getChildren()) - 1:
                ret += '''
                    <input
                        type="image"
                        src="/static/img/downarrow.svg"
                        name="down_{}"
                        i18n:attributes="title mask_edit_down_title"
                        class="mediatum-icon-small"
                    />
                    '''.format(item.id)
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            ret += '''
                    <input
                        type="image"
                        src="/static/img/edit-pen-paper.svg"
                        name="edit_{}"
                        i18n:attributes="title mask_edit_edit_row"
                        class="mediatum-icon-small"
                    />
                    <input
                        type="image"
                        src="/static/img/cancel.svg"
                        name="delete_{}"
                        i18n:attributes="title mask_edit_delete_row"
                        onClick="return questionDel()"
                        class="mediatum-icon-small"
                    />
                </div>
                '''.format(item.id)
            ret += '</div>'

        return ret

    def getMetaEditor(self, item, req):
        """ editor mask for label definition """
        fields = []
        metadatatype = req.params.get("metadatatype")

        if req.params.get("op", "") == "new":
            pidnode = q(Node).get(req.params.get("pid"))
            if pidnode.get("type") in ("vgroup", "hgroup"):
                for field in pidnode.all_children:
                    if field.type == "maskitem" and field.id != pidnode.id:
                        fields.append(field)
            else:
                for m in metadatatype.getMasks():
                    if ustr(m.id) == ustr(req.params.get("pid")):
                        for field in m.children:
                            fields.append(field)
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))

        return tal.processTAL(
                dict(
                    op=req.params.get("op", ""),
                    pid=req.params.get("pid", ""),
                    item=item,
                    fields=fields,
                   ),
                file="metadata/label.html",
                macro="metaeditor",
                request=req,
               )

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/label.html",
                dict(
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName())
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)
