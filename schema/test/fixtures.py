# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os

from pytest import yield_fixture, fixture

from core.test.fixtures import session_empty, session_default_data
from schema.test.factories import MetadatatypeFactory
from utils.compat import iteritems
logg = logging.getLogger(__name__)

from .factories import *


@fixture
def article_metafields():
    fielddefs = {
        "doi": "text",
        "author": "text",
        "page": "text",
        "title": "text",
        "publisher": "text"
    }
    metafields = [MetafieldFactory(name=n, attrs__type=t) for n, t in iteritems(fielddefs)]
    return metafields


@fixture
def article_citeproc_mask(article_metafields):
    maskitems = []
    for metafield in article_metafields:
        maskitem = FieldMaskitemFactory(name=metafield.name)
        maskitem.children.append(metafield)
        maskitems.append(maskitem)
    mask = CiteprocMaskFactory()
    mask.children.extend(maskitems)
    return mask


@fixture
def journal_article_mdt(article_citeproc_mask, article_metafields):
    mdt = DocumentMetadatatypeFactory(name="dt-zeitschriftenaufsatz",
                                      attrs__citeprocmapping="journal-article")
    mdt.children.extend(article_metafields)
    mdt.children.append(article_citeproc_mask)
    return mdt
