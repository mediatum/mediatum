# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import


def cache_key_generator_for_node_argument(namespace, fn, **kw):
    """Generates keys for a function taking a node as first argument. 
    The node ID is used as part of the cache key."""
    fname = fn.__name__
    namespace_prefix = namespace + "_" if namespace else ""
    fix_key = namespace_prefix + "_" + fname 
    
    def gen_key(node, *args):
        other_args = ("_" + "_".join(str(a) for a in args)) if args else ""
        return fix_key + str(node.id) + other_args
    
    return gen_key
