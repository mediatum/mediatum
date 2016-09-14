# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import string

import factory
from factory import fuzzy

from schema.schema import Metadatatype, Metafield, Mask, Maskitem
from schema.mapping import MappingField, Mapping
from core.test.factories import SQLAFactory


class MetadatatypeFactory(SQLAFactory):
    class Meta:
        model = Metadatatype
        
    name = factory.LazyAttributeSequence(lambda o, n: "Metadatatype#{}".format(n))


class DocumentMetadatatypeFactory(MetadatatypeFactory):
    attrs = factory.Dict({
        "datatypes": "article",
        "active": 1,
        "citeprocmapping": "article"
    })


class MetafieldFactory(SQLAFactory):
    class Meta:
        model = Metafield
        
    name = factory.LazyAttributeSequence(lambda o, n: "Metafield#{}".format(n))
    attrs = factory.Dict({
        "label": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })


class TextMetafieldFactory(MetafieldFactory):
    attrs = factory.Dict({
        "type": "text",
        "label": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })


class CheckMetafieldFactory(MetafieldFactory):
    attrs = factory.Dict({
        "type": "check",
        "label": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })



class FieldMaskitemFactory(SQLAFactory):
    class Meta:
        model = Maskitem
        
    attrs = factory.Dict({
        "required": 0,
        "type": "field"
    })


class MaskFactory(SQLAFactory):
    class Meta:
        model = Mask

    attrs = factory.Dict({
        "masktype": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })
    
    
class CiteprocMaskFactory(MaskFactory):
    name = "citeproc"
    attrs = factory.Dict({
        "defaultmask": True,
        "masktype": "export"
    })


class CiteprocMappingFactory(SQLAFactory):
    class Meta:
        model = Mapping
        
    attrs = factory.Dict({
        "active": 1,
        "footer": "}",
        "header": "{",
        "separator": ",",
        "standardformat": "[field]: [value]", 
        "mappingtype": "citeproc"
    })


class MappingFieldFactory(SQLAFactory):
    class Meta:
        model = MappingField
        
    attrs = factory.Dict({
        "mandatory": False
    })