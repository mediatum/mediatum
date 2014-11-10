# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import os

from pytest import yield_fixture, fixture

from core.file import File
from core.test.factories import NodeFactory, DocumentFactory, DirectoryFactory
from core import db
logg = logging.getLogger(__name__)


@yield_fixture
def session_empty():
    s = db.session
    transaction = s.connection().begin()
    yield s
    transaction.rollback()
    s.close()


@yield_fixture
def session_default_data():
    from core.database.init import init_database_values
    s = db.session
    init_database_values(s)
    transaction = s.connection().begin()
    yield s
    transaction.rollback()
    s.close()


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
    print some_node, container_node, content_node
    some_node.children.extend([container_node, content_node])
    some_node.files.append(some_file)
    return some_node


@fixture
def some_node_with_sort_children(some_node, other_container_node, other_content_node):
    some_node.children.extend([other_container_node, other_content_node])
    return some_node


@fixture
def parent_node(some_node, other_content_node, other_container_node):
    some_node.children.append(other_content_node)
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
