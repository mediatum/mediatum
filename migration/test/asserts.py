# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import print_function
from utils.compat import iteritems

def assert_access_rule(access_rule, **attrs_to_check):

    attrs = dict(group_ids=None, dateranges=None, subnets=None, invert_group=False, invert_date=False, invert_subnet=False)
    attrs.update(attrs_to_check)
    for attrname, value in iteritems(attrs):
        assert getattr(access_rule, attrname) == value
        
