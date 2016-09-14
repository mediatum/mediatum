# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details

Web API node iteration functions.
"""
import logging

from itertools import islice, tee
from utils.compat import iteritems

logg = logging.getLogger(__name__)


global all_node_ids_cached
all_node_ids_cached = None

# id of the collections node
COLLECTIONS_NODE_ID = 10


def all_node_id_gen(api, start_node_id=COLLECTIONS_NODE_ID):
    """Generates all node ids in the tree starting from `start_node_id`"""
    top_collections = iteritems(api.children_shortlist(start_node_id))
    it = None
    while True:
        if not it:
            collection_nid, collection_name, _ = next(top_collections)
            logg.info("fetching all children of top collection %s (%s)", collection_name, collection_nid)
            it = api.allchildren_shortlist(collection_nid).iterids()
        try:
            nid = next(it)
        except StopIteration:
            it = None
        yield nid


def visit_all_nodes(api, get_func, check_func=None, start=None, use_id_cache=False):
    """Visits all data nodes in the tree by running a function given by `get_func`.
    :param api: API instance to use
    :param get_func: the function that will be called for each data node id
    :param check_func: function that will be called on the result of `get_func`.
        This function should raise an Exception if something is wrong with the result.
    :param start: number of nodes to skip at the beginning
    :param use_id_cache: if True, use cached node ids from a previous visit run. This is much faster.
            Can be used if your database doesn't change between runs.
    """
    global all_node_ids_cached
    if use_id_cache:
        if all_node_ids_cached:
            all_node_ids, all_node_ids_cached = tee(all_node_ids_cached)
        else:
            logg.info("using cached node ids")
            all_node_ids, all_node_ids_cached = tee(all_node_id_gen(api))
    else:
        all_node_ids = all_node_id_gen(api)

    if start:
        all_node_ids = islice(all_node_ids, start)
    visited_nids = set()
    exceptions = {}
    for nid in all_node_ids:
        if nid not in visited_nids:
            try:
                node = get_func(nid)
                if check_func:
                    check_func(node)
            except Exception as e:
                logg.warn("node %s failed", nid)
                exceptions[nid] = e
            visited_nids.add(nid)
            visited_count = len(visited_nids)
            if visited_count % 1000 == 0:
                logg.info("%s nodes visited, %s exceptions", visited_count, len(exceptions))

    return visited_nids, exceptions
