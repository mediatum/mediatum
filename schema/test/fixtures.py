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


METAFIELDS = [
    ("DOI", "text"),
    ("author", "ilist"),
    ("page", "text"),
    ("title", "text"),
    ("publisher", "text"),
    ("issued", "date"),
]

ARTICLE_METAFIELDS = METAFIELDS + []

@fixture(scope="session")
def article_metafields():
    metafields = [MetafieldFactory(name=n, attrs__type=t) for n, t in ARTICLE_METAFIELDS]
    return metafields


@fixture(scope="session")
def article_citeproc_mask(article_metafields):
    # create citeproc export mapping
    metafield_to_mappingfield = {}
    for metafield in article_metafields:
        mappingfield = MappingFieldFactory(name=metafield.name)
        metafield_to_mappingfield[metafield] = mappingfield
        
    exportmapping = CiteprocMappingFactory()
    exportmapping.children.extend(itervalues(metafield_to_mappingfield))
    
    from core import db
    # we need the actual node ids later in this fixture, which are only assigned after a flush
    db.session.flush()
    
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


@fixture(scope="session")
def journal_article_mdt(article_citeproc_mask, article_metafields):
    mdt = DocumentMetadatatypeFactory(name="dt-zeitschriftenaufsatz",
                                      attrs__citeprocmapping="journal-article;_default;misc")
    mdt.children.extend(article_metafields)
    mdt.children.append(article_citeproc_mask)
    return mdt


@fixture(scope="session")
def default_mdt(journal_article_mdt):
    return journal_article_mdt
