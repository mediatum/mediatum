# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import string
from base64 import b64encode
import factory.alchemy
from factory.fuzzy import *
import scrypt

from contenttypes import Directory, Collection, Document, Collections, Home
from core import Node, User, UserGroup, AuthenticatorInfo, File
from core import db
from core.auth import INTERNAL_AUTHENTICATOR_KEY
from core.systemtypes import Root


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


class FuzzyEmail(FuzzyText):

    def fuzz(self):
        local = "".join(random.choice(self.chars) for _ in range(self.length))
        domain = "".join(random.choice(self.chars) for _ in range(self.length)) + ".org"
        return u"{}{}@{}{}".format(self.prefix, local, domain, self.suffix)


class UserFactory(SQLAFactory):

    salt = "salt" * 8
    password_hash = b64encode(scrypt.hash("test", salt))

    class Meta:
        model = User

    login_name = FuzzyText(length=6, chars=string.lowercase)
    display_name = FuzzyText(length=6, chars=string.lowercase)
    firstname = FuzzyText(length=6, chars=string.lowercase)
    lastname = FuzzyText(length=6, chars=string.lowercase)
    email = FuzzyEmail(length=6, chars=string.lowercase)
    comment = FuzzyText(length=15, chars=string.lowercase)
    telephone = FuzzyText(length=12, chars=string.digits)
    organisation = FuzzyText(length=6, chars=string.lowercase)
    can_change_password = FuzzyChoice([True, False])


class UserGroupFactory(SQLAFactory):

    class Meta:
        model = UserGroup

    name = FuzzyText(length=6, chars=string.lowercase)
    description = FuzzyText(length=15, chars=string.lowercase)
    is_editor_group = FuzzyChoice([True, False])
    is_workflow_editor_group = FuzzyChoice([True, False])
    hidden_edit_functions = factory.List([u"identifier", u"search"])


class DocumentFactory(NodeFactory):

    class Meta:
        model = Document
    schema = u"testschema"


ContentNodeFactory = DocumentFactory


def make_simple_nodeclass_factory(nodecls):
    class NodeClassFactory(NodeFactory):
        class Meta:
            model = nodecls

    return NodeClassFactory

DirectoryFactory = make_simple_nodeclass_factory(Directory)
CollectionFactory = make_simple_nodeclass_factory(Collection)
CollectionsFactory = make_simple_nodeclass_factory(Collections)
HomeFactory = make_simple_nodeclass_factory(Home)
RootFactory = make_simple_nodeclass_factory(Root)


class AuthenticatorInfoFactory(SQLAFactory):

    class Meta:
        model = AuthenticatorInfo

    auth_type = FuzzyText(length=6, chars=string.lowercase)
    name = FuzzyText(length=6, chars=string.lowercase)


class InternalAuthenticatorInfoFactory(AuthenticatorInfoFactory):

    class Meta:
        model = AuthenticatorInfo

    auth_type = INTERNAL_AUTHENTICATOR_KEY[0]
    name = INTERNAL_AUTHENTICATOR_KEY[1]


class FileFactory(SQLAFactory):

    class Meta:
        model = File

    path = FuzzyText(length=20, chars=string.lowercase)
    mimetype = FuzzyText(length=6, chars=string.lowercase)
    filetype = FuzzyText(length=6, chars=string.lowercase)
