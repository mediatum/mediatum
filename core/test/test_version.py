# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import yield_fixture, raises
from sqlalchemy_continuum.utils import version_class

from core import db, Node, File
from core.database.postgres.alchemyext import truncate_tables
from contenttypes import Directory
from core.test.factories import DirectoryFactory


@yield_fixture
def session(session_unnested):
    """XXX: sqlalchemy-continuum goes crazy if run with the normal session fixture.
    This here works but leaves rows in the database that must removed in the teardown function for this module.
    Adding more tests can lead to failures because data from previous tests could interfere with newly created objects.
    It would be better to clean up after each test or find out why continuum doesn't work with the normal session fixture.
    """
    yield session_unnested


def teardown_module(module):
    """Clean up the database mess ;)"""
    db.enable_session_for_test()
    truncate_tables()
    db.session.commit()
    db.disable_session_for_test()


def test_plain(content_node):
    db.session.commit()
    assert content_node.versions.count() == 1


def test_add_child(container_node):
    node = container_node
    d = DirectoryFactory()
    # Note: sqlalchemy-continuum creates versions only if the node itself changes. Adding a relationship doesn't create a new version!
    db.session.commit()
    node.children.append(d)
    # set attr to force a new version
    node[u"changed"] = u"new_child"
    db.session.commit()
    assert container_node.versions[0].children.count() == 0
    assert container_node.versions[1].children.count() == 1


def test_remove_child(container_node):
    node = container_node
    d = DirectoryFactory()
    node.children.append(d)
    db.session.commit()
    node.children = []
    node[u"changed"] = u"removed_child"
    db.session.commit()
    assert container_node.versions[0].children.count() == 1
    assert container_node.versions[1].children.count() == 0


def test_add_file(container_node):
    node = container_node
    db.session.commit()
    d = File(path=u"test", filetype=u"test", mimetype=u"test")
    node.files.append(d)
    node[u"changed"] = u"new_file"
    db.session.commit()
    assert node.versions[0].files.count() == 0
    assert node.versions[1].files.count() == 1


def test_remove_file(container_node):
    node = container_node
    d = File(path=u"test", filetype=u"test", mimetype=u"test")
    node.files.append(d)
    db.session.commit()
    node.files = []
    node[u"changed"] = u"removed_file"
    db.session.commit()
    assert node.versions[0].files.count() == 1
    assert node.versions[1].files.count() == 0


def test_replace_file(container_node):
    from core import File
    node = container_node
    db.session.commit()
    d = File(path=u"test", filetype=u"test", mimetype=u"test")
    node.files.append(d)
    node[u"testattr"] = u"test"
    db.session.commit()
    d = File(path=u"replaced", filetype=u"test", mimetype=u"test")
    node.files = [d]
    node[u"testattr"] = u"replaced"
    db.session.commit()
    assert node.versions[1].files.one().path == u"test"
    assert node.versions[2].files.one().path == u"replaced"


def test_change_file(container_node):
    from core import File
    node = container_node
    d = File(path=u"test", filetype=u"test", mimetype=u"test")
    node.files.append(d)
    db.session.commit()
    d.path = u"changed"
    db.session.commit()
    # Changing the current file affects only the current node's File, not the node version's File.
    assert node.versions[0].files.one().path == u"test"
    assert node.files.one().path == u"changed"
    assert node.versions[-1].next is None


def test_change_attr(content_node):
    s = db.session
    node = content_node
    s.commit()
    node[u"attr"] = u"test"
    s.commit()
    node[u"attr"] = u"test_changed"
    s.commit()
    assert node.versions.count() == 3
    assert node.versions[1].get(u"attr") == u"test"
    assert node.versions[-1].next is None



def test_delete_attr(content_node):
    s = db.session
    node = content_node
    node[u"attr"] = u"to_delete"
    s.commit()
    del node[u"attr"]
    s.commit()
    assert node.versions.count() == 2
    assert u"attr" not in node.versions[1]


def test_revert_attrs(content_node):
    s = db.session
    s.commit()
    node = content_node
    node[u"attr"] = u"test"
    s.commit()
    node[u"attr"] = u"test_changed"
    s.commit()
    assert node.versions.count() == 3
    assert node.versions[2][u"attr"] == u"test_changed"
    node.versions[0].revert()
    s.commit()
    assert u"attr" not in node
    assert node.versions[-1].next is None


def test_call_nodeclass_method(content_node):
    assert content_node.versions[0].getSchema() == u"testschema"


def test_use_node_property(content_node):
    vers = content_node.versions[0]
    assert vers.attributes == vers.attrs


def test_use_content_property(content_node):
    vers = content_node.versions[0]
    # XXX: maybe find a better test subject than metadatatype which doesn't fail ;)
    with raises(Exception) as e:
        vers.metadatatype
    assert u"testschema" in e.value.message

# legacy versioning support


def test_isActiveVersion_node(content_node):
    assert content_node.isActiveVersion()


def test_getActiveVersion_node(content_node):
    assert content_node.getActiveVersion() == content_node


def test_isActiveVersion_older_version(content_node_versioned):
    node = content_node_versioned
    assert node.versions[0].isActiveVersion() == False


def test_isActiveVersion_current_version(content_node_versioned):
    node = content_node_versioned
    assert node.versions[2].isActiveVersion() == True


def test_getActiveVersion_version(content_node_versioned):
    node = content_node_versioned
    assert node.versions[1].getActiveVersion() == node


def test_versions(content_node_versioned):
    assert content_node_versioned.versions.count() == 3


def test_getVersionList(content_node_versioned_tagged):
    assert len(content_node_versioned_tagged.getVersionList()) == 1


def test_old_node_version_support(content_node_versioned_with_alias_id):
    """Tests the q(Node).get hack (in MtQuery)"""
    node = content_node_versioned_with_alias_id
    q = db.query
    version = q(Node).get(23)
    version_cls = version_class(node.__class__)
    assert isinstance(version, version_cls)
    assert version.orderpos == 23


def test_tag(content_node_versioned):
    node = content_node_versioned
    node.tag = u"5"
    assert node.tag == u"5"


def test_create_new_tagged_version(content_node_versioned, some_user):
    node = content_node_versioned
    user = some_user
    # commit user
    db.session.commit()

    with node.new_tagged_version(tag=u"tag", comment=u"comment", user=user) as tx:
        node.orderpos = 100

    assert node.versions.count() == 4
    assert tx.meta[u"tag"] == u"tag"
    assert tx.meta[u"comment"] == u"comment"
    assert tx.user == user

    new_version = node.versions[-1]
    assert u"orderpos" in new_version.changeset
    assert new_version.changeset[u"orderpos"] == [42, 100]
    assert new_version.next is None


def test_create_new_tagged_version_initial_version_tag(content_node_versioned):
    node = content_node_versioned

    with node.new_tagged_version():
        node.orderpos = 100

    new_version = node.versions[-1]
    assert new_version.tag == u"2"


def test_create_new_tagged_version_next_version_tag(content_node_versioned_tagged):
    node = content_node_versioned_tagged

    with node.new_tagged_version():
        node.orderpos = 100

    new_version = node.versions[-1]
    assert new_version.tag == u"3"


def test_create_new_tagged_version_dirty(content_node_versioned):
    node = content_node_versioned

    db.session.add(node.__class__())

    with raises(Exception) as einfo:
        with node.new_tagged_version():
            node.orderpos = 100

    assert "Refusing" in einfo.value.message
    
    
