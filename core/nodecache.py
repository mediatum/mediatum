# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from sqlalchemy.orm import undefer, joinedload
from dogpile.cache.region import make_region
from sqlalchemy.orm.exc import NoResultFound


class Cache(object):
    pass

memory_nodecache = make_region().configure('dogpile.cache.memory')


def get_typed_node_from_cache(nodeclass, nid):    
    """Returns a node instance for the given node id. 
    Fetches the requested node from the DB if it's not in the cache.
    The type is checked against `nodeclass` when the object is loaded from the DB.
    If the node does not exist or has the wrong type, NoResultFound is thrown.
    """
    from core import db
    s = db.session

    def fetch_typed_node_from_db():
        return s.query(nodeclass).options(undefer(nodeclass.attrs), 
                                           undefer(nodeclass.system_attrs), 
                                           joinedload(nodeclass.file_objects)).filter_by(id=nid).one()
        

    node_from_cache = memory_nodecache.get_or_create(nodeclass, fetch_typed_node_from_db)
    return s.merge(node_from_cache, load=False)


def get_singleton_node_from_cache(nodeclass):    
    """Returns the singleton instance for the given node class. 
    Fetches the requested singleton from the DB if it's not in the cache.
    """
    from core import db
    s = db.session

    def fetch_singleton_node_from_db():
        return s.query(nodeclass).options(undefer(nodeclass.attrs), 
                                           undefer(nodeclass.system_attrs), 
                                           joinedload(nodeclass.file_objects)).one()

    node_from_cache = memory_nodecache.get_or_create(nodeclass, fetch_singleton_node_from_db)
    return s.merge(node_from_cache, load=False)
        
    
def get_root_node():
    """Root object may not change during runtime, so we can cache it indefinitely"""
    from core.systemtypes import Root
    return get_singleton_node_from_cache(Root)


def get_collections_node():
    """Collections object may not change during runtime, so we can cache it indefinitely"""
    from contenttypes import Collections
    return get_singleton_node_from_cache(Collections)


def get_home_root_node():
    """Home object may not change during runtime, so we can cache it indefinitely"""
    from contenttypes import Home
    return get_singleton_node_from_cache(Home)
