# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import factory.alchemy

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
    name = factory.LazyAttributeSequence(lambda o, n: u"{}#{}".format(o.type, n))


class UserFactory(NodeFactory):
    class Meta:
        model = User


class DocumentFactory(NodeFactory):
    class Meta:
        model = Document
    schema = u"testschema"


class DirectoryFactory(NodeFactory):
    class Meta:
        model = Directory