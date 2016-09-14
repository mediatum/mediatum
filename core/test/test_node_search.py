# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import fixture
from core import db, Setting
from core.test.factories import DocumentFactory

LANGUAGES = [u"dutch", u"english"]


@fixture
def search_node(session, container_node):
    session.query(Setting).get(u"search.fulltext_autoindex_languages").value = LANGUAGES
    session.query(Setting).get(u"search.attribute_autoindex_languages").value = LANGUAGES
    session.flush()
    d1 = DocumentFactory(attrs={u"date": u"2015-08-18T12:48:24.894752", u"title": u"postgres ftw", u"lang": u"english"})
    d1.fulltext = u"The big blue elephant jumped over the crippled blue dolphin."
    container_node.content_children.append(d1)
    d2 = DocumentFactory(attrs={u"date": u"2013-01-11T00:42:23.081500", u"title": u"postgres fts", u"lang": u"dutch"})
    d2.fulltext = u"Een blauwe olifant springt al dartelend over de kreupele dolfijn."
    container_node.content_children.append(d2)
    dummy = DocumentFactory()
    dummy.fulltext = u"und nun zu etwas völlig Anderem"
    container_node.content_children.append(dummy)
    return container_node


def run_search(node, searchquery):
    return node.search(searchquery, languages=LANGUAGES)


def test_search_miss(search_node):
    hits = run_search(search_node, u"full=miss").all()
    assert len(hits) == 0


def test_search_compare_attr(search_node):
    hits = run_search(search_node, u"date < 2014-11-11").all()
    assert len(hits) == 1
    assert hits[0][u"lang"] == u"dutch"


def test_search_fulltext(search_node):
    hits = run_search(search_node, u"fulltext=dolphin").all()
    assert len(hits) == 1
    assert hits[0][u"lang"] == u"english"


def test_search_attr(search_node):
    hits = run_search(search_node, u"title=ftw").all()
    assert len(hits) == 1


def test_search_full(search_node):
    hits = run_search(search_node, u"full=postgres").all()
    assert len(hits) == 2


def test_search_or(search_node):
    hits = run_search(search_node, u"full=elephant or full=olifant").all()
    assert len(hits) == 2


def test_search_modify_fulltext(search_node):
    child = search_node.content_children.first()
    child.fulltext = u"now to something completely different"
    hits = run_search(search_node, u"fulltext=different").all()
    assert len(hits) == 1


def test_search_modify_attrs(search_node):
    child = search_node.content_children.first()
    child[u"newattr"] = u"newattr"
    hits = run_search(search_node, u"full=newattr").all()
    assert len(hits) == 1
