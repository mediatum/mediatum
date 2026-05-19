# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Provide (functions that return) singleton
objects from the database so these object
do not have to be loaded in each request.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging

import backports.functools_lru_cache as _backports_functools_lru_cache
import sqlalchemy as _sqlalchemy
import sqlalchemy.orm as _sa_orm

import core as _core

_logg = _logging.getLogger(__name__)


@_backports_functools_lru_cache.lru_cache(maxsize=None)
def _get_singleton_node_from_cache(nodeclass):
    """
    Returns the singleton instance for the given node class.
    Fetches the requested singleton
    from the DB if it's not in the cache.
    """
    node = _core.db.session.query(nodeclass).options(
            _sa_orm.undefer(nodeclass.attrs),
            _sa_orm.undefer(nodeclass.system_attrs),
            _sa_orm.joinedload(nodeclass.file_objects),
           ).one()
    # without expunge, we see random `DetachedInstanceError`s
    _core.db.session.expunge(node)
    return node


def _get_singleton_node(nodeclass):

    node = _get_singleton_node_from_cache(nodeclass)
    inspect = _sqlalchemy.inspect(node)
    if inspect.modified or inspect.deleted or inspect.was_deleted:
        _logg.debug("clearing node cache, as the cached %s object got changed", nodeclass.__name__)
        _get_singleton_node_from_cache.cache_clear()
        node = _get_singleton_node_from_cache(nodeclass)
    return _core.db.session.merge(node, load=False)


def init():
    get_root_node()
    get_collections_node()
    get_home_root_node()
    get_workflows_node()
    get_mappings_node()
    get_metadatatypes_node()


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


def get_workflows_node():
    """Workflows object may not change during runtime, so we can cache it indefinitely"""
    from workflow.workflow import Workflows
    return _get_singleton_node(Workflows)


def get_mappings_node():
    """Mappings object may not change during runtime, so we can cache it indefinitely"""
    from core.systemtypes import Mappings
    return _get_singleton_node(Mappings)


def get_metadatatypes_node():
    """Metadatatypes object may not change during runtime, so we can cache it indefinitely"""
    from core.systemtypes import Metadatatypes
    return _get_singleton_node(Metadatatypes)
