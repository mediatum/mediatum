# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os

from pytest import yield_fixture, fixture

from core.test.factories import NodeFactory, DocumentFactory, DirectoryFactory, UserFactory, UserGroupFactory,\
    InternalAuthenticatorInfoFactory, FileFactory, CollectionFactory, HomeFactory, CollectionsFactory, RootFactory
from core import db
from contenttypes.container import Collections, Home
from core.database.init import init_database_values
from core.init import load_system_types, load_types, init_fulltext_search, init_db_connector, update_nodetypes_in_db
from core.database.postgres.user import AuthenticatorInfo, create_special_user_dirs
from sqlalchemy import event
from core.database.postgres.alchemyext import truncate_tables
from core.archive import Archive
from core.transition.app import AthanaFlaskStyleApp
logg = logging.getLogger(__name__)


def autouse_session():
    """Call this to autouse the session fixture"""
    @yield_fixture(autouse=True)
    def session(session):
        yield session

    return session


@fixture(scope="session")
def database():
    """Connect to the DB and drop/create mediatum schema for a clean environment"""
    db.enable_session_for_test()
    db.configure()
    db.create_engine()
    db.drop_schema()
    db.create_schema(set_alembic_version=False)
    init_fulltext_search()
    update_nodetypes_in_db()
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
def root(session):
    return RootFactory()

@fixture
def internal_authenticator_info(session):
    return InternalAuthenticatorInfoFactory()


@fixture
def some_user(session, internal_authenticator_info):
    user = UserFactory()
    user.authenticator_info = internal_authenticator_info
    return user


@fixture
def user_with_home_dir(some_user, home_root):
    from contenttypes import Directory
    home = Directory(name=u"Arbeitsverzeichnis (test)")
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
def guest_user(internal_authenticator_info):
    guest_group = UserGroupFactory(is_editor_group=False, is_workflow_editor_group=False, is_admin_group=False)
    from core import config
    user = UserFactory(login_name=config.get_guest_name())
    user.groups.append(guest_group)
    user.authenticator_info = internal_authenticator_info
    return user


@fixture
def internal_user(some_user, internal_authenticator_info):
    some_user.authenticator_info = internal_authenticator_info
    some_user.login_name = u"testuser"
    some_user.can_change_password = True
    return some_user


@fixture
def some_group(session):
    return UserGroupFactory()


@fixture
def some_file(session):
    """Create a File model without creating a real file"""
    node = NodeFactory()
    return FileFactory(node=node, path=u"testfilename", filetype=u"testfiletype", mimetype=u"testmimetype")


@fixture
def some_file_in_subdir(session):
    """Create a File model with a dir in the path without creating a real file"""
    node = NodeFactory()
    return FileFactory(node=node, path=u"test/filename", filetype=u"testfiletype", mimetype=u"testmimetype")


@yield_fixture
def some_file_real(some_file):
    """Create a File model and the associated file on the filesystem.
    File is deleted after the test
    """
    with some_file.open("w") as wf:
        wf.write("test")
    try:
        yield some_file
    finally:
        if some_file.exists:
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
def some_node(content_node, container_node):
    attrs = {
        u"testattr": u"testvalue"
    }
    system_attrs = {
        u"testattr": u"system.testvalue"
    }
    some_node = DirectoryFactory(name=u"somenode", attrs=attrs, system_attrs=system_attrs)
    parent = DirectoryFactory(name=u"parent")
    parent.children.append(some_node)
    some_node.children.extend([container_node, content_node])
    return some_node

@fixture
def some_node_with_file(some_node):
    some_file = FileFactory()
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


@fixture
def content_node_versioned(content_node):
    db.session.commit()
    content_node.orderpos = 23
    db.session.commit()
    content_node.orderpos = 42
    db.session.commit()
    return content_node


@fixture
def content_node_versioned_tagged(content_node_versioned):
    content_node_versioned.versions.first().tag = u"2"
    db.session.commit()
    return content_node_versioned


@fixture
def content_node_versioned_with_alias_id(session, content_node):
    from sqlalchemy_continuum import versioning_manager
    session.commit()
    content_node.orderpos = 42
    session.commit()
    uow = versioning_manager.unit_of_work(session)
    tx = uow.create_transaction(session)
    tx.meta = {u"alias_id": 23}
    content_node.orderpos = 23
    session.commit()
    return content_node


@fixture(scope="session")
def internal_authenticator():
    from core.auth import InternalAuthenticator, INTERNAL_AUTHENTICATOR_KEY
    return InternalAuthenticator(INTERNAL_AUTHENTICATOR_KEY[1])


@fixture
def fake_archive():
    from core.archive import register_archive

    class FakeArchive(Archive):

        archive_type = "test"

        def __init__(self):
            self.loaded_node_paths = set()

        def get_local_filepath(self, node):
            os.path.join("/teststorage/", self.get_archive_path(node))

        def fetch_file_from_archive(self, node):
            self.loaded_node_paths.add(self.get_archive_path(node))

        def get_state(self, node):
            if self.get_archive_path(node) in self.loaded_node_paths:
                return Archive.PRESENT
            return Archive.NOT_PRESENT

    archive = FakeArchive()
    register_archive(archive)
    return archive


@fixture
def app():
    app = AthanaFlaskStyleApp("test")
    return app


@yield_fixture
def req(app, guest_user):
    with app.test_request_context() as ctx:
        yield ctx.request


@yield_fixture
def enable_athana_continuum_plugin():
    from core import db
    db.athana_continuum_plugin.disabled = False
    yield
    db.athana_continuum_plugin.disabled = True
    
