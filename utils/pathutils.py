"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

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

def createPath(parent_node, sPath, sSeparator='/'):
    dirs = string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName) > 0:
            dir_node = Node(dirName, 'directory')
            parent_node.children.append(dir_node)
            parent_node = dir_node
    db.session.commit()
    return parent_node


def createPathPreserve(parent_node, sPath, sSeparator='/'):
    dirs = string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName) > 0:
            node = parent_node.children.filter_by(name=dirName).one()
            parent_node = node
            if not isinstance(node, Node):
                dir_node = Node(dirName, 'directory')
                parent_node.children.append(dir_node)
                parent_node = dir_node
    db.session.commit()
    return parent_node


def createPathPreserve2(parent_node, sPath, sType='directory', sSeparator='/'):
    dirs = string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName) > 0:
            node = parent_node.children.filter_by(name=dirName).one()
            parent_node = node
            if not isinstance(node, Node):
                dir_node = Node(dirName, sType)
                parent_node.children.append(dir_node)
                parent_node = dir_node
    db.session.commit()
    return parent_node


def checkPath(parent_node, sPath, sSeparator='/'):
    dirs = string.split(sPath, sSeparator)
    for dirName in dirs:
        if len(dirName) > 0:
            parent_node = parent_node.children.filter_by(name=dirName).one()
            if not isinstance(parent_node, Node):
                return None
    return parent_node

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


def getSubdirsContaining(path, filelist=[]):
    '''returns those (direct) sub folders of path containing all files from filelist'''
    if not os.path.exists(path):  # path not found
        return []

    result = [p for p in os.listdir(path) if os.path.isdir(os.path.join(path, p))]
    if filelist:
        result = [d for d in result if set(filelist).issubset(os.listdir(os.path.join(path, d)))]
    return result


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
    from core.nodecache import get_collections_node, get_root_node
    if node_query is None:
        node_query = q(Node)

    group_ids, ip, date = build_accessfunc_arguments()
    excluded_node_ids = [get_root_node().id]

    f = mediatumfunc.accessible_container_paths(node.id, excluded_node_ids, group_ids, ip, date)
    id_paths = [t[0] for t in db.session.execute(f).fetchall()]
    # fetch all nodes at once to reduce DB load
    
    if not id_paths:
        return []
    
    path_nodes = node_query.filter(Node.id.in_(chain(*id_paths)))

    # convert node ids to nodes
    nid_to_node ={n.id: n for n in path_nodes}
    node_paths = [[nid_to_node.get(nid) for nid in id_path] for id_path in id_paths]
    return node_paths
    