# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import print_function
from utils.compat import iteritems



def assert_access_rule(access_rule, invert=None, blocking=None, **attrs_to_check):
    # we must flush the rule first to gain access to column default values
    from core import db
    db.session.add(access_rule)
    db.session.flush()
    attrs = dict(group_ids=None, dateranges=None, subnets=None, invert_group=False, invert_date=False, invert_subnet=False)
    attrs.update(attrs_to_check)
    for attrname, expected_value in iteritems(attrs):
        value = getattr(access_rule, attrname) 
        assert value == expected_value


def assert_access_rule_with_flags(access_rule_with_flags, invert=None, blocking=None, **attrs_to_check):
    access_rule, flags = access_rule_with_flags
    assert_access_rule(access_rule, **attrs_to_check)
    if invert is not None:
        assert flags[0] == invert
        
    if blocking is not None:
        assert flags[1] == blocking
