# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import string

import factory.alchemy
from factory import fuzzy

from core import db
from schema.schema import Metadatatype, Metafield, Mask, Maskitem


class SQLAFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_SESSION = db.session


class MetadatatypeFactory(SQLAFactory):
    FACTORY_FOR = Metadatatype
    name = factory.LazyAttributeSequence(lambda o, n: "Metadatatype#{}".format(n))


class DocumentMetadatatypeFactory(MetadatatypeFactory):
    attrs = factory.Dict({
        "datatypes": "article",
        "active": 1,
        "citeprocmapping": "article"
    })


class MetafieldFactory(SQLAFactory):
    FACTORY_FOR = Metafield
    name = factory.LazyAttributeSequence(lambda o, n: "Metafield#{}".format(n))
    attrs = factory.Dict({
        "label": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })


class TextMetafieldFactory(MetafieldFactory):
    attrs = factory.Dict({
        "type": "text",
        "label": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })


class FieldMaskitemFactory(SQLAFactory):
    FACTORY_FOR = Maskitem
    attrs = factory.Dict({
        "required": 0,
        "type": "field"
    })


class CiteprocMaskFactory(SQLAFactory):
    FACTORY_FOR = Mask
    name = "citeproc"
    attrs = factory.Dict({
        "defaultmask": True,
        "masktype": "export"
    })
