# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from utils.pathutils import get_accessible_paths
from utils.testing import make_node_public, append_chain_of_containers


def test_get_accessible_paths_multiple(session, req, root, home_root, collections, content_node):
    node = content_node
    
    root.children.append(collections)
    path_nodes_1 = append_chain_of_containers(2, collections)
    path_nodes_2 = append_chain_of_containers(3, collections)
    
    path_nodes_1[-1].content_children.append(content_node)
    path_nodes_2[-1].content_children.append(content_node)
    
    make_node_public(path_nodes_2[1], "read")
    session.flush()
    
    # only one path should be found because the guest user cannot see the nodes in path_nodes_1
    paths = get_accessible_paths(node) 
    assert len(paths) == 1
    path = paths[0]
    assert len(path) == 3
    
    # first node of path_nodes_2 is the collections root, the tested function omits this node because it's not public
    assert path == path_nodes_2[1:]
