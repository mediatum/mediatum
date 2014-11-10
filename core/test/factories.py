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
    FACTORY_SESSION = db.session


class NodeFactory(SQLAFactory):
    FACTORY_FOR = Node
    id = factory.Sequence(lambda n: n)
    type = u"node"
    orderpos = 1
    name = factory.LazyAttributeSequence(lambda o, n: u"{}#{}".format(o.type, n))


class UserFactory(NodeFactory):
    FACTORY_FOR = User
    type = u"user"


class DocumentFactory(NodeFactory):
    FACTORY_FOR = Document
    type = u"document"
    schema = u"testschema"


class DirectoryFactory(NodeFactory):
    FACTORY_FOR = Directory
    type = u"directory"
