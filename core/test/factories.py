# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import string
import factory.alchemy
from factory import fuzzy

from contenttypes import Directory
from contenttypes import Document
from core.node import Node
from core.user import User
from core import db


class SQLAFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session = db.make_session


class NodeFactory(SQLAFactory):
    class Meta:
        model = Node
    id = factory.Sequence(lambda n: n)
    orderpos = 1
    
    # XXX: is there a better way for getting the model name? This is so crazy...
    @classmethod
    def model_name(cls):
        return cls._meta.model.__name__
    
    name = factory.LazyAttributeSequence(lambda o, n: u"{}#{}".format(o._LazyStub__model_class.model_name(), n))


class UserFactory(NodeFactory):
    class Meta:
        model = User
    
    attrs = factory.Dict({
        "service.userkey": fuzzy.FuzzyText(length=6, chars=string.lowercase)
    })

class DocumentFactory(NodeFactory):
    class Meta:
        model = Document
    schema = u"testschema"


class DirectoryFactory(NodeFactory):
    class Meta:
        model = Directory