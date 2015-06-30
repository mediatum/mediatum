# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
from core.search import parser


def test_parse_full_unicode():
    parser.parse_string(u'full="Öffentliche schöne Häuser in München"')
    