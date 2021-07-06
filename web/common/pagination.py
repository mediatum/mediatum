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

default_edit_nodes_per_page = 20


def get_nodes_per_page(nodes_per_page, dir):
    if dir and not nodes_per_page:
        nodes_per_page = dir.get('nodes_per_page')
    if nodes_per_page:
        nodes_per_page = int(nodes_per_page)
    return nodes_per_page or default_edit_nodes_per_page
