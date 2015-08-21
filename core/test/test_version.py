# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function

from contenttypes import Directory
from pytest import fixture
from sqlalchemy_continuum import versioning_manager
from core import db, Node
from sqlalchemy_continuum.utils import version_class

# XXX: sqlalchemy-continuum overwrites the first version of a node somehow. This doesn't happen if the code is run outside of an unit test.
# Investigate this...


def test_plain(content_node):
    db.session.commit()
    assert content_node.versions.count() == 1


def test_add_child(container_node):
    d = Directory("dir")
    container_node.children.append(d)
    db.session.flush()
    # we want to know if the new child relation is also present in the nodemapping_version table
    assert container_node.versions[0].children.count() == 1


def test_change_attr(content_node):
    s = db.session
    node = content_node
    s.commit()
    node["attr"] = "test"
    s.commit()
    node["attr"] = "test_changed"
    s.commit()
    assert node.versions.count() == 2
    assert node.versions[0].get("attr") == "test"


def test_delete_attr(content_node):
    s = db.session
    node = content_node
    node["attr"] = "to_delete"
    s.commit()
    del node["attr"]
    s.commit()
    assert node.versions.count() == 1
    assert "attr" not in node.versions[0]


def test_revert_attrs(content_node):
    s = db.session
    s.commit()
    node = content_node
    node["attr"] = "test"
    s.commit()
    node["attr"] = "test_changed"
    s.commit()
    assert node.versions.count() == 2
    assert node.versions[1]["attr"] == "test_changed"
    node.versions[0].revert()
    s.commit()
    assert node["attr"] == "test"


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
    assert node.versions[1].isActiveVersion() == True


def test_getActiveVersion_version(content_node_versioned):
    node = content_node_versioned
    assert node.versions[1].getActiveVersion() == node


def test_versions(content_node_versioned):
    assert content_node_versioned.versions.count() == 2


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

