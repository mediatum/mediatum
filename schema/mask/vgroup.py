# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging as _logging

import mediatumtal.tal as _tal

import core.translation as _core_translation
from schema.schema import getMetadataType, getAllMetaFields, VIEW_DATA_ONLY, Maskitem
from core.metatype import Metatype
from core import Node, db
from utils.utils import suppress


_logg = _logging.getLogger(__name__)
q = db.query


class m_vgroup(Metatype):

    def getFormHTML(self, field, nodes, req):
        ret = '<fieldset>'
        if field.getLabel() != "":
            ret += '<legend>' + field.getLabel() + '</legend>'

        for item in field.getChildren().sort_by_orderpos():
            if item.get("type") in ("hgroup", "vgroup", "field", "label"):
                f = getMetadataType(item.get("type"))
                ret += f.getFormHTML(item, nodes, req)
            else:
                _logg.error("wrong field")
        ret += '</fieldset>'
        return ret

    def getViewHTML(self, field, nodes, flags, language=None, template_from_caller=None, mask=None, use_label=True):
        if flags & VIEW_DATA_ONLY:
            ret = []
            for item in field.getChildren().sort_by_orderpos():
                f = getMetadataType(item.get("type"))
                ret.append(f.getViewHTML(item, nodes, flags, language=language))
            return ret
        else:
            # standard view

            ret = '<div class="mask_row"><fieldset>\n'
            if use_label:
                ret += '<legend>' + field.getLabel() + '</legend>'
            for item in field.getChildren().sort_by_orderpos():
                f = getMetadataType(item.get("type"))
                ret += '<div class="mask_row">' + f.getViewHTML(item, nodes, flags) + '</div>\n'
            ret += '</fieldset></div>\n'

        return ret

    def getMetaHTML(self, parent, index, sub=False, language=None, fieldlist={}):
        item = parent.getChildren().sort_by_orderpos()[index]
        ret = ''
        i = 0

        if not sub:
            ret += '<div id="' + unicode(item.id) + '" class="row" onmouseover="pick(this)" onmouseout="unpick(this)" onclick="select(this)">'
        ret += '<fieldset style="cursor:hand">'

        if item.getLabel() != "":
            ret += '<legend>' + item.getLabel() + '</legend>'

        for field in item.getChildren().sort_by_orderpos():
            f = getMetadataType(field.get("type"))
            ret += f.getMetaHTML(item, i, True, language=language, fieldlist=fieldlist) + '<br/>'
            i += 1

        if len(item.getChildren()) == 0:
            ret += '<span i18n:translate="mask_editor_no_fields">- keine Felder definiert -</span>'

        ret += '</fieldset>'

        if not sub:
            ret += '<div align="right" id="' + unicode(item.id) + \
                '_sub" style="display:none"><small style="color:silver">(' + (item.get("type")) + ')</small>'
            if index > 0:
                ret += '<input type="image" src="/img/uparrow.png" name="up_' + \
                    unicode(item.id) + '" i18n:attributes="title mask_edit_up_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            if index < len(parent.getChildren()) - 1:
                ret += '<input type="image" src="/img/downarrow.png" name="down_' + \
                    unicode(item.id) + '" i18n:attributes="title mask_edit_down_title"/>'
            else:
                ret += '&nbsp;&nbsp;&nbsp;'
            ret += ' <input type="image" src="/img/edit.png" name="edit_' + unicode(
                item.id) + '" i18n:attributes="title mask_edit_edit_row"/> <input type="image" src="/img/delete.png" name="delete_' + unicode(
                item.id) + '" i18n:attributes="title mask_edit_delete_row" onClick="return questionDel()"/></div>'
            ret += '</div>'

        return ret

    def getMetaEditor(self, item, req):
        """ editor mask for vgroup-field definition """
        fieldlist = getAllMetaFields()
        if len(item.getParents()) == 0:
            pid = req.params.get("pid", "")
        else:
            pid = item.getParents()[0].id

        if req.params.get("edit") == "None":
            item = Maskitem(name="", type="maskitem")
            item.set("type", "vgroup")

        details = ""
        i = 0
        for field in item.getChildren().sort_by_orderpos():
            f = getMetadataType(field.get("type"))
            details += f.getMetaHTML(item, i, False, fieldlist=fieldlist, language=_core_translation.lang(req))
            i += 1

        if req.params.get("sel_id", "") != "":
            i = 0
            for id in req.params.get("sel_id")[:-1].split(";"):
                f = getMetadataType(q(Node).get(id).get("type"))
                with suppress(TypeError, warn=False):
                    details += f.getMetaHTML(item, i, False, itemlist=req.params.get("sel_id")
                                             [:-1].split(";"), ptype="vgroup", fieldlist=fieldlist)
                i += 1
        fields = []
        metadatatype = req.params.get("metadatatype")

        if req.params.get("op", "") == "new":
            pidnode = q(Node).get(req.params.get("pid"))
            if pidnode.get("type") in ("vgroup", "hgroup"):
                for field in pidnode.all_children:
                    if field.getType().getName() == "maskitem" and field.id != pidnode.id:
                        fields.append(field)
            else:
                for m in metadatatype.getMasks():
                    if ustr(m.id) == ustr(req.params.get("pid")):
                        for field in m.getChildren():
                            fields.append(field)
        fields.sort(lambda x, y: cmp(x.getOrderPos(), y.getOrderPos()))

        v = {}
        v["pid"] = pid
        v["item"] = item
        v["op"] = req.params.get("op", "")
        v["details"] = details
        v["fields"] = fields
        v["selid"] = req.params.get("sel_id", "")
        return _tal.processTAL(v, file="schema/mask/vgroup.html", macro="metaeditor", request=req)

    @classmethod
    def isContainer(cls):
        return True

    def getName(self):
        return "maskfieldtype_vgroup"
