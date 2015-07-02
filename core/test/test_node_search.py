# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from core import db


def test_search_full(container_node):
    db.session.flush()
    res = container_node.search("full=test")
    # this doesn't find anything, just a quick function test
    assert res.all() == []
    

def test_search_compare_attr(container_node):
    db.session.flush()
    res = container_node.search("date > 2014-11-11")
    # this doesn't find anything, just a quick function test
    assert res.all() == []
    

def test_search_fulltext(container_node):
    db.session.flush()
    res = container_node.search("fulltext=test")
    # this doesn't find anything, just a quick function test
    assert res.all() == []
    

def test_search_attr(container_node):
    db.session.flush()
    res = container_node.search("title=test")
    # this doesn't find anything, just a quick function test
    assert res.all() == []
    

def test_search_or(container_node):
    db.session.flush()
    res = container_node.search("full=test or full=haus")
    # this doesn't find anything, just a quick function test
    assert res.all() == []
    
