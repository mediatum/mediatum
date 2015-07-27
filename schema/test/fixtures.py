# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os

from pytest import yield_fixture, fixture

from utils.compat import iteritems, itervalues
logg = logging.getLogger(__name__)

from .factories import *
from core.test.fixtures import content_node, session


METAFIELDS = [
    ("DOI", "text"),
    ("author", "ilist"),
    ("page", "text"),
    ("title", "text"),
    ("publisher", "text"),
    ("issued", "date"),
]

ARTICLE_METAFIELDS = METAFIELDS + []

@fixture
def some_metafield():
    """Doesn't make much sense, but ok for hierarchy / getter testing"""
    metafield = MetafieldFactory()
    return metafield
    
@fixture
def some_maskitem():
    """Doesn't make much sense, but ok for hierarchy / getter testing"""
    metafield = MetafieldFactory()
    maskitem = FieldMaskitemFactory()
    maskitem.children.append(metafield)
    return maskitem


@fixture
def some_mask_with_maskitem(some_maskitem):
    """Doesn't make much sense, but ok for hierarchy / getter testing"""
    mask = MaskFactory()
    mask.maskitems.append(some_maskitem)
    return mask

    
@fixture
def some_mask_with_nested_maskitem(some_mask_with_maskitem):
    """Doesn't make much sense, but ok for hierarchy / getter testing"""
    mask = some_mask_with_maskitem
    metafield = MetafieldFactory()
    nested_maskitem = FieldMaskitemFactory()
    nested_maskitem.children.append(metafield)
    mask.maskitems[0].children.append(nested_maskitem)
    return mask
    
    
@fixture
def article_metafields():
    metafields = [MetafieldFactory(name=n, attrs__type=t) for n, t in ARTICLE_METAFIELDS]
    return metafields


@fixture
def article_citeproc_mask(article_metafields):
    # create citeproc export mapping
    metafield_to_mappingfield = {}
    for metafield in article_metafields:
        mappingfield = MappingFieldFactory(name=metafield.name)
        metafield_to_mappingfield[metafield] = mappingfield
        
    exportmapping = CiteprocMappingFactory()
    exportmapping.children.extend(itervalues(metafield_to_mappingfield))
    
    # we need the actual node ids later in this fixture, which are only assigned after a flush
    from core import db; db.session.flush()
    
    # create mask
    maskitems = []
    for metafield in article_metafields:
        mappingfield = metafield_to_mappingfield[metafield]
        maskitem = FieldMaskitemFactory(name=metafield.name, 
                                        attrs__mappingfield=mappingfield.id,
                                        attrs__attribute=metafield.id)
        maskitem.children.append(metafield)
        maskitems.append(maskitem)
    mask = CiteprocMaskFactory()
    mask.maskitems.extend(maskitems)
    mask["exportmapping"] = exportmapping.id
    return mask


some_mask = article_citeproc_mask


@fixture
def journal_article_mdt(article_citeproc_mask, article_metafields):
    mdt = DocumentMetadatatypeFactory(name="dt-zeitschriftenaufsatz",
                                      attrs__citeprocmapping="journal-article;_default;misc")
    mdt.children.extend(article_metafields)
    mdt.children.append(article_citeproc_mask)
    return mdt


@fixture
def default_mdt(journal_article_mdt):
    return journal_article_mdt


@fixture
def some_mdt_with_masks():
    mdt = DocumentMetadatatypeFactory()
    mdt.masks.append(MaskFactory())
    mdt.masks.append(MaskFactory(name="mask_de", attrs__language="de"))
    mdt.masks.append(MaskFactory(name="mask_en", attrs__language="en"))
    mdt.masks.append(MaskFactory(name="mask_en_2", attrs__language="en", attrs__masktype="testmasktype"))
    return mdt


@fixture
def content_node_with_mdt(some_mdt_with_masks, content_node):
    content_node.schema = some_mdt_with_masks.name
    return content_node
    
