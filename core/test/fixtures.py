# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os

from pytest import yield_fixture, fixture

from core.test.factories import NodeFactory, DocumentFactory, DirectoryFactory, UserFactory, UserGroupFactory,\
    InternalAuthenticatorInfoFactory, FileFactory, CollectionFactory, HomeFactory, CollectionsFactory
from core import db
from contenttypes.container import Collections, Home
from core.database.init import init_database_values
from core.init import load_system_types, load_types, init_fulltext_search, init_db
from core.database.postgres.user import AuthenticatorInfo, create_special_user_dirs
from sqlalchemy import event
from core.database.postgres.alchemyext import truncate_tables
logg = logging.getLogger(__name__)


def autouse_session():
    """Call this to autouse the session fixture"""
    @yield_fixture(autouse=True)
    def session(session):
        yield session

    return session


@fixture(scope="session")
def database():
    """Connect to the DB, drop/create schema and load models"""
    db.enable_session_for_test()
    db.connect()
    s = db.session
    s.execute("DROP SCHEMA IF EXISTS mediatum CASCADE")
    s.execute("CREATE schema mediatum")
    s.commit()
    db.create_all()
    load_system_types()
    load_types()
    init_fulltext_search()
    db.disable_session_for_test()
    return db


@yield_fixture
def session(database):
    """Yields default session which is closed after the test.
    A SAVEPOINT is created before running the test that always rolls back.
    The savepoint is restarted automatically if the test code does a rollback.
    (see http://docs.sqlalchemy.org/en/rel_1_0/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
    Enables db.session. Without this fixture, session operations are not possible.
    Tip: use session = autouse_session() in conftest.py if you need the session for all tests in a package.
    """
    db = database
    db.enable_session_for_test()
    conn = db.engine.connect()
    tx = conn.begin()
    db.Session.configure(bind=conn)
    s = db.session
    s.begin_nested()

    @event.listens_for(s, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()
    # run the isolated test...
    yield s
    s.close()
    tx.rollback()
    # just a quick test if the rollback removed all pending nodes created in the test
    from core import Node
    assert db.session.query(Node).count() == 0
    conn.close()
    db.Session.remove()
    db.disable_session_for_test()


@yield_fixture
def session_truncate(database):
    """
    Alternative version of session() that truncates all tables after the test instead of using nested transactions.
    This is much slower than session().
    It's better to use the session fixture, but this is needed for some tests that have problems with nested transactions
    (sqlalchemy-continuum, for example).
    Enables db.session. Without this or the session fixture, session operations are not possible.
    """
    db = database
    db.enable_session_for_test()
    db.Session.configure(bind=db.engine)
    s = db.session
    yield s
    s.rollback()
    truncate_tables()
    s.commit()
    db.Session.remove()
    db.disable_session_for_test()


@yield_fixture
def session_unnested(database):
    """
    Alternative version of session() that does not wrap the session in a transaction.
    WARNING: objects can remain in the database and later tests may fail!
    It's better to use the session fixture, but this is needed for some tests that have problems with nested transactions
    (sqlalchemy-continuum, for example).
    Enables db.session. Without this or the session fixture, session operations are not possible.
    """
    db = database
    db.enable_session_for_test()
    db.Session.configure(bind=db.engine)
    s = db.session
    yield s
    s.rollback()
    db.Session.remove()
    db.disable_session_for_test()


@fixture
def default_data(session):
    """Initial data needed for normal mediaTUM operations
    """
    init_database_values(db.session)


# @fixture(scope="session")
# def session_default_data():
#     from core.database.init import init_database_values
#     s = db.session
#     return init_database_values(s)


@fixture
def collections(session):
    return CollectionsFactory(name="collections")


@fixture
def home_root(session):
    return HomeFactory()


@fixture
def some_user(session):
    return UserFactory()


@fixture
def user_with_home_dir(some_user, home_root):
    from contenttypes import Directory
    home = Directory(name="Arbeitsverzeichnis (test)")
    home.children.extend(create_special_user_dirs())
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
def internal_authenticator_info(session):
    return InternalAuthenticatorInfoFactory()


@fixture
def internal_user(some_user, internal_authenticator_info):
    some_user.authenticator_info = internal_authenticator_info
    some_user.login_name = "testuser"
    some_user.can_change_password = True
    return some_user


@fixture
def some_group(session):
    return UserGroupFactory()


@fixture
def some_file(session):
    """Create a File model without creating a real file"""
    return FileFactory(path=u"testfilename", filetype=u"testfiletype", mimetype=u"testmimetype")


@fixture
def some_file_in_subdir(session):
    """Create a File model with a dir in the path without creating a real file"""
    return FileFactory(path=u"test/filename", filetype=u"testfiletype", mimetype=u"testmimetype")


@yield_fixture
def some_file_real(some_file):
    from core import File
    """Create a File model and the associated file on the filesystem.
    File is deleted after the test
    """
    with some_file.open("w") as wf:
        wf.write("test")
    yield some_file
    os.unlink(some_file.abspath)


@fixture
def content_node(session):
    return DocumentFactory(name=u"content", orderpos=1, attrs=dict(sortattr=6))


@fixture
def other_content_node(session):
    return DocumentFactory(name=u"a_content", orderpos=2, attrs=dict(sortattr=5))


@fixture
def other_content_node_2(session):
    return DocumentFactory(name=u"b_content", orderpos=2)


@fixture
def container_node(session):
    return DirectoryFactory(name=u"container", orderpos=3, attrs=dict(sortattr=8))


@fixture
def other_container_node(session):
    return DirectoryFactory(name=u"a_container", orderpos=4, attrs=dict(sortattr=7))


@fixture
def some_node(content_node, container_node, some_file):
    attrs = {
        u"testattr": u"testvalue"
    }
    some_node = DirectoryFactory(name=u"somenode", attrs=attrs)
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
