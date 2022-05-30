# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import operator as _operator
import os
import string
from warnings import warn
from core import db
from core import Node
from contenttypes import Collections
from core.systemtypes import Root
from core.database.postgres.alchemyext import exec_sqlfunc
from core.database.postgres import mediatumfunc, build_accessfunc_arguments
from itertools import chain
from core.nodecache import get_home_root_node

q = db.query

# scaled down version of web.frontend.contend.getPaths() to get all paths


def getBrowsingPathList(node):
    warn("use get_accessible_paths()", DeprecationWarning)
    from contenttypes import Container
    list = []
    collections = q(Collections).one()
    root = q(Root).one()

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
            elif isinstance(node, Container):
                paths.append(node)
    if len(list) > 0:
        return list
    else:
        return []


def isDescendantOf(node, parent):
    warn("use node.is_descendant_of(parent)", DeprecationWarning)
    return node.is_descendant_of(parent)


def getPaths(node):
    warn("use get_accessible_paths()", DeprecationWarning)
    res = []

    def r(node, path):
        node = node.getActiveVersion()
        if isinstance(node, Root):
            return
        for p in node.getParents():
            path.append(p)
            if not isinstance(p, Collections):
                r(p, path)
        return path

    paths = []

    p = r(node, [])
    omit = 0
    if p:
        for node in p:
            if node.has_read_access() or node.type in ("home", "root"):
                if node.type in ("directory", "home", "collection") or node.type.startswith("directory"):
                    paths.append(node)
                if isinstance(node, (Collections, Root)):
                    paths.reverse()
                    if len(paths) > 0 and not omit:
                        res.append(paths)
                    omit = 0
                    paths = []
            else:
                omit = 1
    if len(res) > 0:
        return res
    else:
        return []


def get_accessible_paths(node, node_query=None):
    from core.nodecache import get_root_node

    # fetch all paths (with nid and access right flag) from db
    paths = mediatumfunc.accessible_container_paths(node.id, *build_accessfunc_arguments())
    paths = map(_operator.itemgetter(0), db.session.execute(paths).fetchall())

    # convert node ids to nodes
    # fetch all nodes at once to reduce DB load
    nid2node = {node.id:node for node in (node_query or q(Node)).filter(
                                Node.id.in_(chain(*(tuple(nid for nid,_ in path) for path in paths))))}

    root_id = get_root_node().id
    return frozenset(tuple(nid2node[nid] for nid,access in path if access and nid!=root_id) for path in paths)
