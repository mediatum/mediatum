# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


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
