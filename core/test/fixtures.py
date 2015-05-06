# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os

from pytest import yield_fixture, fixture

from core import File
from core.test.factories import NodeFactory, DocumentFactory, DirectoryFactory, UserFactory, UserGroupFactory
from core import db
from contenttypes.container import Collections, Home
from core.database.init import init_database_values
from core.init import load_system_types, load_types
from core.systemtypes import Users, UserGroups
from core.database.postgres.user import AuthenticatorInfo
logg = logging.getLogger(__name__)


@fixture(scope="session", autouse=True)
def database():
    """Connect to the DB, drop/create schema and load models"""
    db.session.execute("DROP schema mediatum CASCADE")
    db.session.execute("CREATE schema mediatum")
    db.session.commit()
    db.create_all()
    load_system_types()
    load_types()
    return db


@yield_fixture(autouse="True")
def session():
    """Yields default session which is closed after the test.
    Inner actions are wrapped in a transaction that always rolls back.
    """
    s = db.session 
    s.begin(subtransactions=True)
    yield s
    s.rollback()
    s.close()
    

@fixture
def default_data():
    """Initial data needed for normal mediaTUM operations
    """
    init_database_values(db.session)


# @fixture(scope="session")
# def session_default_data():
#     from core.database.init import init_database_values
#     s = db.session
#     return init_database_values(s)


@fixture
def collections():
    return Collections("collections")

@fixture
def home_root():
    return Home("home")


@fixture
def some_user():
    return UserFactory()

@fixture
def user_with_home_dir(some_user, home_root):
    from contenttypes import Directory
    home = Directory(name="Arbeitsverzeichnis (test)")
    home.children.extend([Directory("faulty"), Directory("upload"), Directory("trash")])
    home_root.children.append(home)
    some_user.home_dir = home
    return some_user

@fixture
def editor_user(some_user):
    editor_group = UserGroupFactory(is_editor_group=True, is_workflow_editor_group=False, is_admin_group=False)
    some_user.groups.append(editor_group)
    return some_user

@fixture
def workflow_editor_user(some_user):
    workflow_editor_group = UserGroupFactory(is_editor_group=False, is_workflow_editor_group=True, is_admin_group=False)
    some_user.groups.append(workflow_editor_group)
    return some_user

@fixture
def admin_user(some_user):
    admin_group = UserGroupFactory(is_editor_group=False, is_workflow_editor_group=False, is_admin_group=True)
    some_user.groups.append(admin_group)
    return some_user

@fixture
def internal_authenticator_info():
    from core.auth import INTERNAL_AUTHENTICATOR_KEY
    return AuthenticatorInfo(auth_type=INTERNAL_AUTHENTICATOR_KEY[0], name=INTERNAL_AUTHENTICATOR_KEY[1])

@fixture
def internal_user(some_user, internal_authenticator_info):
    some_user.authenticator_info = internal_authenticator_info
    some_user.login_name = "testuser"
    some_user.can_change_password = True
    return some_user


@fixture
def some_group():
    return UserGroupFactory()


@fixture
def some_file():
    """Create a File model without creating a real file"""
    return File(path=u"testfilename", filetype=u"testfiletype", mimetype=u"testmimetype")


@fixture
def some_file_in_subdir():
    """Create a File model with a dir in the path without creating a real file"""
    return File(path=u"test/filename", filetype=u"testfiletype", mimetype=u"testmimetype")


@yield_fixture
def some_file_real(some_file):
    """Create a File model and the associated file on the filesystem.
    File is deleted after the test
    """
    with some_file.open("w") as wf:
        wf.write("test")
    yield some_file
    os.unlink(some_file.abspath)


@fixture
def content_node():
    return DocumentFactory(name=u"content", orderpos=1, attrs=dict(sortattr=6))


@fixture
def other_content_node():
    return DocumentFactory(name=u"a_content", orderpos=2, attrs=dict(sortattr=5))


@fixture
def other_content_node_2():
    return DocumentFactory(name=u"b_content", orderpos=2)


@fixture
def container_node():
    return DirectoryFactory(name=u"container", orderpos=3, attrs=dict(sortattr=8))


@fixture
def other_container_node():
    return DirectoryFactory(name=u"a_container", orderpos=4, attrs=dict(sortattr=7))


@fixture
def some_node(content_node, container_node, some_file):
    attrs = {
        u"testattr": u"testvalue"
    }
    some_node = DirectoryFactory(name=u"somenode", attrs=attrs)
    some_node.read_access = u"read_access"
    some_node.write_access = u"write_access"
    some_node.data_access = u"data_access"
    parent = DirectoryFactory(name=u"parent")
    parent.children.append(some_node)
    some_node.children.extend([container_node, content_node])
    some_node.files.append(some_file)
    return some_node


@fixture
def some_node_with_sort_children(some_node, other_container_node, other_content_node):
    some_node.children.extend([other_container_node, other_content_node])
    return some_node


@fixture
def parent_node(some_node, other_content_node, other_container_node, other_content_node_2):
    other_container_node.children.append(other_content_node)
    some_node.content_children[0].content_children.append(other_content_node_2)
    some_node.container_children[0].children.extend([other_content_node, other_container_node])
    return some_node.parents[0]


@fixture(params=[u"children", u"container_children", u"content_children"])
def child_query_for_some_node(request, some_node_with_sort_children):
    return getattr(some_node_with_sort_children, request.param)


@fixture
def some_node_with_two_parents(some_node):
    a_parent = NodeFactory(name=u"a_parent")
    a_parent.children.append(some_node)
    return some_node


@fixture(scope="session")
def internal_authenticator():
    from core.auth import InternalAuthenticator, INTERNAL_AUTHENTICATOR_KEY
    return InternalAuthenticator(INTERNAL_AUTHENTICATOR_KEY[1])