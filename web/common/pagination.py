# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
move get_nodes_per_page from web/edit/edit_common.py. Parameters are nodes_per_page
from request parameters or dir as node. default_edit_nodes_per_page is returned in case
parameter is not given.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import backports.functools_lru_cache as _backports_functools_lru_cache
import decimal as _decimal

import core as _core


@_backports_functools_lru_cache.lru_cache()
def get_config_nodes_per_page(edit=True):
    cfgkey = "config.edit-pagination" if edit else "config.view-pagination"
    npps = _core.config.getlist(cfgkey, _core.config.getlist("config.view-pagination", [20, 50, 100]))
    return tuple(e if e == 'all' else int(e) for e in npps)


def get_default_nodes_per_page(edit):
    return get_config_nodes_per_page(edit)[0]


def get_nodes_per_page(nodes_per_page, dir, edit=True):
    inf = _decimal.Decimal("Infinity")
    all2inf = lambda v: inf if v == "all" else int(v)

    npp = dir.get('nodes_per_page') if dir and not nodes_per_page else nodes_per_page
    npp = npp or get_default_nodes_per_page(edit)
    npp = inf if npp == "all" else int(npp)

    npp_def = all2inf(get_default_nodes_per_page(edit))
    npps = list(set(map(all2inf, get_config_nodes_per_page(edit)))) + [npp]
    assert min(npps) > 0
    npps.sort(reverse=npp > npp_def)  # sort such that we always can round "upwards" in the list
    npp = npps[npps.index(npp) + 1]  # this round towards the default value

    return "all" if npp == inf else int(npp)  # replace inf by string "all" again
