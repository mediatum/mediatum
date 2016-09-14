# -*- coding: utf-8 -*-
"""

Test PostgresSQL-specific implementation details of Node.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import raises


def test_container_parent_container_child(session, container_node, other_container_node):
    container_node.container_children.append(other_container_node)
    session.flush()
    assert other_container_node.subnode == False


def test_container_parent_content_child(session, container_node, content_node):
    container_node.content_children.append(content_node)
    session.flush()
    assert content_node.subnode == False


def test_content_parent_content_child(session, content_node, other_content_node):
    content_node.content_children.append(other_content_node)
    session.flush()
    assert other_content_node.subnode


def test_content_node_multiple_content_parents(session, content_node, other_content_node, other_content_node_2):
    other_content_node.content_children.append(content_node)
    other_content_node_2.content_children.append(content_node)
    session.flush()
    assert content_node.subnode
