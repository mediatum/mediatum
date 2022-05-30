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


from sqlalchemy.orm import undefer, joinedload
import backports.functools_lru_cache as _backports_functools_lru_cache
import sqlalchemy.orm as _sa_orm

import core as _core


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
    return _core.db.session.merge(
            _get_singleton_node_from_cache(nodeclass),
            load=False,
           )


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
