# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import operator as _operator

import mediatumtal.tal as _tal

import core.translation as _core_translation
import utils.utils as _utils_utils
from utils.utils import formatLongText
from utils.strings import ensure_unicode

import re as _re
import schema.schema as _schema
from schema.schema import getMetadataType, VIEW_DATA_ONLY, VIEW_SUB_ELEMENT, VIEW_HIDE_EMPTY, VIEW_DATA_EXPORT
from core.metatype import Metatype
from core import db
from core.database.postgres.node import Node

q = db.query
s = db.session


_metafield_type_allowed_chars = _re.compile(r'[a-z]').match


class m_field(Metatype):

    name = "field"

    def set_default_metadata(self, maskitem, node):
        """
        create/set metadata of a document if the value is not set to a default value;
        the default value is obtained from the field type class' method `get_default_value`.
        :param maskitem: field of mask defining metadata
        :param node: document
        :return: None
        """
        metafield = maskitem.getField()
        key = metafield.getName()
        if node.get_special(key) or maskitem.getDefault():
            return
        value = getMetadataType(metafield.get("type")).get_default_value(metafield)
        if value is not None:
            node.set(key, value)


    def getFormHTML(self, field, nodes, req):
        """ create editor field (editarea)"""
        metafield = field.getField()
        metafield_type = metafield.get("type")
        assert _metafield_type_allowed_chars(metafield_type)
        values = tuple(node.get_special(metafield.name) for node in nodes)
        editor_html_form = getMetadataType(metafield_type).editor_get_html_form(metafield,
                            metafield_name_for_html=_schema.sanitize_metafield_name(metafield.name),
                            values=values,
                            required=field.get_required(),
                            language=_core_translation.set_language(req.accept_languages),
                       )
        tal_ctx = dict(
                name=_schema.sanitize_metafield_name(metafield.name),
                description=field.getDescription() or None,
                fieldtype=metafield_type,
                label=field.getLabel(),
                conflict=editor_html_form.conflict,
                required=field.get_required(),
                html_form=editor_html_form.html,
               )
        return _tal.processTAL(tal_ctx, file="schema/mask/field.html", macro="editor_get_field", request=req)


    def getViewHTML(self, maskitem, nodes, flags, language=None, template_from_caller=None, mask=None):
        # XXX: this method claims to support multiple nodes. Unfortunately, this is not true at all...
        first_node = nodes[0]
        metafield = maskitem.metafield
        fieldtype = metafield.get("type")
        metatype = getMetadataType(fieldtype)

        if flags & VIEW_DATA_EXPORT:
            return metatype.viewer_get_data(metafield, maskitem, mask, first_node, language, html=0)
        
        value = metatype.viewer_get_data(metafield, maskitem, mask, first_node, language)[1]
        if not flags & VIEW_DATA_ONLY:
            if maskitem.getFormat() != "":
                value = maskitem.getFormat().replace("<value>", value)
            else:
                value = formatLongText(value, metafield)
        else:
            value = ensure_unicode(value)

        value = value.strip()

        if flags & VIEW_HIDE_EMPTY  and not flags & VIEW_DATA_ONLY and not value:
            # hide empty elements
            return u''

        unit = maskitem.getUnit()

        if value and unit:
            value += " " + unit

        if flags & VIEW_DATA_ONLY:
            # return a valuelist
            return [metafield.name, value, metafield.getLabel(), fieldtype]

        if flags & VIEW_SUB_ELEMENT:
            # metafield in hgroup
            # only using value omitting label, delimiter like '&nbsp;' may be inserted in hgroup.getViewHTML
            return value

        maskitem_label = maskitem.getLabel()
        if maskitem_label:
            label = maskitem_label + u":"
        else:
            label = u'&nbsp;'

        return u'<dt class="mask_label">{}</dt>\n<dd class="mask_value">{}</dd>\n'.format(_utils_utils.esc(label), value)

    def getMetaHTML(self, parent, index, sub=False, language=None, itemlist=[], ptype="", fieldlist={}):
        """ return formated row for metaeditor """
        if len(itemlist) > 0:
            # parent still not existing
            item = q(Node).get(itemlist[index])
            pitems = len(itemlist)
        else:
            item = parent.getChildren().sort_by_orderpos()[index]
            ptype = parent.get("type")
            pitems = len(parent.getChildren())

        field = item.getField()

        if field:
            html_form = u"{} {}".format(
                getMetadataType(field.get("type")).editor_get_html_form(
                    field,
                    metafield_name_for_html=_schema.sanitize_metafield_name(field.name),
                    values=(item.getDefault(),),
                    language=language,
                    required=item.get_required(),
                    ).html,
                item.getUnit(),
            )
        else:  # node for export mask
            attribute = q(Node).get(item.get("attribute"))
            field = item
            html_form = u"{} {}".format(
                getMetadataType("mappingfield").editor_get_html_form(
                    field,
                    width=item.getWidth(),
                    value=attribute.getName(),
                    language=language,
                ),
                item.getUnit(),
            )

        if (not sub) and (len(fieldlist.get(field.getName(), ())) > 1):
            multi_title = _core_translation.translate(
                language,
                "mask_edit_multi_label",
                mapping=dict(schemes=u", ".join(schema.getName() for schema in fieldlist[field.getName()])),
            )
        else:
            multi_title = None

        return _tal.processTAL(
            dict(
                name=_schema.sanitize_metafield_name(field.name),
                fieldtype=_schema.sanitize_metafield_name(field.get('type')),
                conflict=None,
                html_form=html_form,
                description=item.getDescription() or None,
                item_id=item.id,
                required=item.get_required(),
                is_sub=sub,
                label=item.getLabel(),
                is_first=index==0,
                is_last=index==pitems-1,
                multi_title=multi_title,
            ),
            file="schema/mask/field.html",
            macro="admin_get_field_for_maskedit",
        )

    def getMetaEditor(self, item, req):
        """ editor mask for field definition """
        fields = []
        mask = None

        if "pid" in req.values:
            pidnode = None
        else:
            for pidnode in item.getParents():
                with _utils_utils.suppress(Exception,warn=False):
                    if pidnode.getMasktype() == "export":
                        break
            else:
                pidnode = None

        metadatatype = req.params.get("metadatatype")
        if req.params.get("op", "") == "new":
            pidnode = q(Node).get(req.params.get("pid"))
            mask = pidnode
            while (mask.type == 'maskitem'):
                mask = mask.parents[0]

            for m in metadatatype.getMasks():
                if ustr(m.id) == ustr(req.params.get("pid")):
                    fields.extend(m.getChildren())

        fields.sort(key=_operator.methodcaller("getOrderPos"))

        metafields = metadatatype.getMetaFields()
        if mask:
            mask_metafieldnames = frozenset(
                    _schema.sanitize_metafield_name(maskitem.metafield.name)
                    for maskitem in mask.all_maskitems if maskitem.metafield
                   )
            metafields = [mf for mf in metafields
                    if _schema.sanitize_metafield_name(mf.name) not in mask_metafieldnames]
        metafields.sort(key=lambda mf:mf.getName().lower())

        tal_ctx = dict(
                op=req.params["op"],
                pid=req.params.get("pid", ""),
                item=item,
                fields=fields,
                translate=_core_translation.translate,
                language=_core_translation.set_language(req.accept_languages),
               )
        if tal_ctx["op"]=="new":
            tal_ctx["metafields"] = metafields
        elif tal_ctx["op"]=="edit":
            tal_ctx["field"] = item.getField()
        else:
            raise AssertionError("unknown op")

        if pidnode and hasattr(pidnode, 'getMasktype') and pidnode.getMasktype() == "export":
            tal_ctx["mappings"] = tuple(q(Node).get(mapping) for mapping in pidnode.getExportMapping())
            if tal_ctx["op"] == "edit":
                assert tal_ctx.get("field") is None # export masks may not have their field as child
                tal_ctx["field"] = q(Node).get(int(item.get('attribute')))
            return _tal.processTAL(tal_ctx, file="schema/mask/field.html", macro="metaeditor_export", request=req)
        else:
            return _tal.processTAL(tal_ctx, file="schema/mask/field.html", macro="metaeditor", request=req)
