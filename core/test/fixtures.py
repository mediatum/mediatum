# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from pytest import yield_fixture, fixture
from core.test.factories import NodeFactory, DocumentFactory, DirectoryFactory
from core.test.setup import db
from core.file import File


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
    return File(path="testfile", filetype="testfiletype", mimetype="testmimetype")


@fixture
def content_node():
    return DocumentFactory(name="content")


@fixture
def container_node():
    return DirectoryFactory(name="container")


@fixture
def some_node(content_node, container_node, some_file):
    attrs = {
        "testattr": "testvalue"
    }
    some_node = NodeFactory(name="somenode", attrs=attrs)
    some_node.read_access = "read_access"
    some_node.write_access = "write_access"
    some_node.data_access = "data_access"
    parent = NodeFactory(name="parent")
    parent.children.append(some_node)
    some_node.children.extend([container_node, content_node])
    some_node.files.append(some_file)
    return some_node
