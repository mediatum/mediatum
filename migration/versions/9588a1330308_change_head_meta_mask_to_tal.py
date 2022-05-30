# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""change_head_meta_mask_to_tal

Revision ID: 9588a1330308
Revises: a5b3aec3bd5b
Create Date: 2021-11-12 05:59:47.554066

"""

# revision identifiers, used by Alembic.
revision = '9588a1330308'
down_revision = 'a5b3aec3bd5b'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys

import lxml.etree as _lxml_etree

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
import core.systemtypes as _systemtypes
import schema.schema as _schema

_q = _core.db.query


def _new_author(attribute):
    assert '"' not in attribute and "'" not in attribute
    return u"""
        <meta tal:repeat="author python:node.get('{}').split(';')" name="citation_author" tal:attributes="content python:(author)"/>
    """.format(attribute)


def _new_pdf_url():
    return u"""
        <meta
         tal:condition="python:bool(node.files.filter_by(filetype=u'document').count()) and (getAccessRights(node) == 'openAccess')"
         name="citation_pdf_url"
         tal:attributes="content python:'https://{}/doc/{}/document.pdf'.format(config_get('host.name'), node.id)"
         />
    """


def _new_publication_date(mapping, attribute):
    assert '"' not in attribute and "'" not in attribute
    assert '"' not in mapping and "'" not in mapping
    return u"""
        <meta tal:condition="python:node.get('{}')!=''" name="{}" tal:attributes="content python:node.get('{}')[:4]"/>
     """.format(attribute, mapping, attribute)


def _new_meta_mapping(mapping, attribute):
    assert '"' not in attribute and "'" not in attribute
    assert '"' not in mapping and "'" not in mapping
    return u"""
        <meta tal:condition="python:node.get('{}')!=''" name="{}" tal:attributes="content python:node.get('{}')"/>
    """.format(attribute, mapping, attribute)


def _new_meta_attribute(mapping, attribute):
    assert '"' not in attribute and "'" not in attribute
    assert '"' not in mapping and "'" not in mapping
    return u'<meta name="{}" content="{}"/>'.format(mapping, attribute)


def _get_tal_expression(mask):
    for maskitem in mask.children:
        attribute = _q(_core.Node).get(maskitem.get("attribute")).name
        mapping = maskitem.get("mappingfield")
        fieldtype = maskitem.get("fieldtype")
        if fieldtype == "mapping":
            mapping = _q(_core.Node).get(mapping).name
            if mapping == "citation_author":
                yield _new_author(attribute)
            elif mapping == "citation_pdf_url":
                yield _new_pdf_url()
            elif mapping == "citation_publication_date":
                yield _new_publication_date(mapping, attribute)
            else:
                yield _new_meta_mapping(mapping, attribute)
        elif fieldtype == "attribute":
            mapping_xml = _lxml_etree.fromstring(mapping)
            if mapping_xml.tag != "meta":
                raise RuntimeError(u"tag: {} is not 'meta'".format(mapping_xml.tag))
            mapping = mapping_xml.attrib["name"]
            attribute = mapping_xml.attrib["content"]
            if mapping == "citation_pdf_url":
                yield _new_pdf_url()
            elif mapping == "citation_publication_date":
                yield _new_publication_date(mapping, attribute)
            else:
                yield _new_meta_attribute(mapping, attribute)
        else:
            raise RuntimeError(u"unknown fieldtype: {}".format(fieldtype))


def _create_new_mask(metadatatype, tal_expression, mask_name):
    if metadatatype.get_mask(mask_name):
        return
    mask = _schema.Mask(mask_name)
    mask.setMasktype("export")
    mask.setSeparator("<br/>")
    metadatatype.children.append(mask)
    _core.db.session.commit()
    maskitem = mask.addMaskitem("mapping", "field", "", unicode(mask.id))
    metafield = metadatatype.all_children.filter(_core.Node.type=='metafield').order_by(_core.Node.name).first()
    maskitem.set("attribute", unicode(metafield.id))
    maskitem.set("fieldtype", "attribute")
    maskitem.set("mappingfield", tal_expression)
    _core.db.session.commit()


def upgrade():
    for metadatatype in _q(_schema.Metadatatypes).one().children:
        head_meta = metadatatype.get_mask('head_meta')
        if not head_meta:
            continue
        if head_meta.children.count() <= 1:
            # head_meta already converted or has no maskitems
            continue
        head_meta_old = metadatatype.get_mask('head_meta_old_nontal')
        if head_meta_old:
            _schema.delete_mask(head_meta_old)
        tal_expression = "[cmd:getTAL]\n" + "".join(_get_tal_expression(head_meta))
        head_meta.name = 'head_meta_old_nontal'
        _create_new_mask(metadatatype, tal_expression, "head_meta")
        _core.db.session.commit()


def downgrade():
    for metadatatype in _q(_schema.Metadatatypes).one().children:
        head_meta_old = metadatatype.get_mask('head_meta_old_nontal')
        if not head_meta_old:
            continue
        head_meta = metadatatype.get_mask('head_meta')
        if head_meta:
            _schema.delete_mask(head_meta)

        head_meta_old.name = 'head_meta'
        _core.db.session.commit()
