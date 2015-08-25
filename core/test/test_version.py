# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import yield_fixture
from sqlalchemy_continuum.utils import version_class

from core import db, Node, File
from core.database.postgres.alchemyext import truncate_tables
from contenttypes import Directory


@yield_fixture
def session(session_unnested):
    """XXX: sqlalchemy-continuum goes crazy if run with the normal session fixture.
    This here works but leaves rows in the database that must removed in the teardown function for this module.
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
    d = Directory("d")
    # Note: sqlalchemy-continuum creates versions only if the node itself changes. Adding a relationship doesn't create a new version!
    db.session.commit()
    node.children.append(d)
    # set attr to force a new version
    node["changed"] = "new_child"
    db.session.commit()
    assert container_node.versions[0].children.count() == 0
    assert container_node.versions[1].children.count() == 1


def test_remove_child(container_node):
    node = container_node
    d = Directory("d")
    node.children.append(d)
    db.session.commit()
    node.children = []
    node["changed"] = "removed_child"
    db.session.commit()
    assert container_node.versions[0].children.count() == 1
    assert container_node.versions[1].children.count() == 0


def test_add_file(container_node):
    node = container_node
    db.session.commit()
    d = File(path="test", filetype="test", mimetype="test")
    node.files.append(d)
    node["changed"] = "new_file"
    db.session.commit()
    assert node.versions[0].files.count() == 0
    assert node.versions[1].files.count() == 1


def test_remove_file(container_node):
    node = container_node
    d = File(path="test", filetype="test", mimetype="test")
    node.files.append(d)
    db.session.commit()
    node.files = []
    node["changed"] = "removed_file"
    db.session.commit()
    assert node.versions[0].files.count() == 1
    assert node.versions[1].files.count() == 0


def test_replace_file(container_node):
    from core import File
    node = container_node
    db.session.commit()
    d = File(path="test", filetype="test", mimetype="test")
    node.files.append(d)
    node["testattr"] = "test"
    db.session.commit()
    d = File(path="replaced", filetype="test", mimetype="test")
    node.files = [d]
    node["testattr"] = "replaced"
    db.session.commit()
    assert node.versions[1].files.one().path == "test"
    assert node.versions[2].files.one().path == "replaced"


def test_change_file(container_node):
    from core import File
    node = container_node
    d = File(path="test", filetype="test", mimetype="test")
    node.files.append(d)
    db.session.commit()
    d.path = "changed"
    db.session.commit()
    # Changing the current file affects only the current node's File, not the node version's File.
    assert node.versions[0].files.one().path == "test"
    assert node.files.one().path == "changed"


def test_change_attr(content_node):
    s = db.session
    node = content_node
    s.commit()
    node["attr"] = "test"
    s.commit()
    node["attr"] = "test_changed"
    s.commit()
    assert node.versions.count() == 3
    assert node.versions[1].get("attr") == "test"


def test_delete_attr(content_node):
    s = db.session
    node = content_node
    node["attr"] = "to_delete"
    s.commit()
    del node["attr"]
    s.commit()
    assert node.versions.count() == 2
    assert "attr" not in node.versions[1]


def test_revert_attrs(content_node):
    s = db.session
    s.commit()
    node = content_node
    node["attr"] = "test"
    s.commit()
    node["attr"] = "test_changed"
    s.commit()
    assert node.versions.count() == 3
    assert node.versions[2]["attr"] == "test_changed"
    node.versions[0].revert()
    s.commit()
    assert "attr" not in node


def test_call_nodeclass_method(content_node):
    assert content_node.versions[0].getSchema() == "testschema"


def test_use_node_property(content_node):
    vers = content_node.versions[0]
    assert vers.attributes == vers.attrs

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


def test_getVersionList(content_node_versioned):
    assert len(content_node_versioned.getVersionList()) == 1


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
    node.tag = "v5"
    assert node.tag == "v5"
