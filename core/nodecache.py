# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from sqlalchemy.orm import undefer, joinedload
from sqlalchemy.orm.exc import NoResultFound
import backports.functools_lru_cache as _backports_functools_lru_cache

from core import db as _db


@_backports_functools_lru_cache.lru_cache(maxsize=128)
def _get_singleton_node_from_cache(nodeclass):
    """Returns the singleton instance for the given node class. 
    Fetches the requested singleton from the DB if it's not in the cache.
    """
    return _db.session.query(nodeclass).options(undefer(nodeclass.attrs),
                                        undefer(nodeclass.system_attrs),
                                        joinedload(nodeclass.file_objects)).one()


def _get_singleton_node(nodeclass):
    return _db.session.merge(_get_singleton_node_from_cache(nodeclass), load=False)


def get_root_node():
    """Root object may not change during runtime, so we can cache it indefinitely"""
    from core.systemtypes import Root
    return _get_singleton_node(Root)


def get_collections_node():
    """Collections object may not change during runtime, so we can cache it indefinitely"""
    from contenttypes import Collections
    return _get_singleton_node(Collections)


def get_home_root_node():
    """Home object may not change during runtime, so we can cache it indefinitely"""
    from contenttypes import Home
    return _get_singleton_node(Home)
