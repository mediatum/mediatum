# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.nodecache import get_collections_node


def test_get_collections_node(req, collections):
    cached_collections = get_collections_node()
    assert cached_collections == collections