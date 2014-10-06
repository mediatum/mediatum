# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from factory import alchemy, fuzzy
import factory
from core.node import Node
from contenttypes.directory import Directory
from core.user import User
from contenttypes.document import Document
from core.test.setup import db


class SQLAFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_SESSION = db.session


class NodeFactory(SQLAFactory):
    FACTORY_FOR = Node
    id = factory.Sequence(lambda n: n)
    type = "node"
    orderpos = 1
    name = factory.LazyAttributeSequence(lambda o, n: "{}#{}".format(o.type, n))


class UserFactory(NodeFactory):
    FACTORY_FOR = User
    type = "user"


class DocumentFactory(NodeFactory):
    FACTORY_FOR = Document
    type = "document"
    schema = "testschema"


class DirectoryFactory(NodeFactory):
    FACTORY_FOR = Directory
    type = "directory"