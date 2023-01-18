# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import operator as _operator
from warnings import warn

import contenttypes as _contenttypes
import contenttypes.container as _
import core as _core
import core.nodecache as _core_nodecache
from core.database.postgres.node import Node
from core.database.postgres import mediatumfunc, build_accessfunc_arguments
from itertools import chain


def getBrowsingPathList(node):
    warn("use get_accessible_paths()", DeprecationWarning)
    list = []
    collections = _core_nodecache.get_collections_node()
    root = _core_nodecache.get_root_node()

    def r(node, path):
        if node is root:
            return
        for p in node.parents:
            path.append(p)
            if p is not collections:
                r(p, path)
        return path

    paths = []

    p = r(node, [])

    if p:
        for node in p:
            if node is collections or node is root:
                paths.reverse()
                if len(paths) > 1:
                    list.append(paths)
                paths = []
            elif isinstance(node, _contenttypes.container.Container):
                paths.append(node)
    if len(list) > 0:
        return list
    else:
        return []


def isDescendantOf(node, parent):
    warn("use node.is_descendant_of(parent)", DeprecationWarning)
    return node.is_descendant_of(parent)


def get_accessible_paths(node, node_query=None):
    # fetch all paths (with nid and access right flag) from db
    paths = mediatumfunc.accessible_container_paths(node.id, *build_accessfunc_arguments())
    paths = map(_operator.itemgetter(0), _core.db.session.execute(paths).fetchall())

    # convert node ids to nodes
    # fetch all nodes at once to reduce DB load
    nid2node = {node.id:node for node in (node_query or _core.db.query(Node)).filter(
                                Node.id.in_(chain(*(tuple(nid for nid,_ in path) for path in paths))))}

    root_id = _core_nodecache.get_root_node().id
    return frozenset(tuple(nid2node[nid] for nid,access in path if access and nid!=root_id) for path in paths)
