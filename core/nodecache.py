# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from sqlalchemy.orm import undefer, joinedload
from sqlalchemy.orm.exc import NoResultFound

from core import db as _db
from utils.lrucache import lru_cache as _lru_cache


@_lru_cache(maxsize=128)
def get_singleton_node_from_cache(nodeclass):    
    """Returns the singleton instance for the given node class. 
    Fetches the requested singleton from the DB if it's not in the cache.
    """
    return _db.session.query(nodeclass).options(undefer(nodeclass.attrs),
                                        undefer(nodeclass.system_attrs),
                                        joinedload(nodeclass.file_objects)).one()


def get_root_node():
    """Root object may not change during runtime, so we can cache it indefinitely"""
    from core.systemtypes import Root
    return _db.session.merge(get_singleton_node_from_cache(Root), load=False)


def get_collections_node():
    """Collections object may not change during runtime, so we can cache it indefinitely"""
    from contenttypes import Collections
    return _db.session.merge(get_singleton_node_from_cache(Collections), load=False)


def get_home_root_node():
    """Home object may not change during runtime, so we can cache it indefinitely"""
    from contenttypes import Home
    return _db.session.merge(get_singleton_node_from_cache(Home), load=False)
