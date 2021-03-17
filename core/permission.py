# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division
from __future__ import print_function

from core import AccessRule, db

q = db.query


def get_or_add_access_rule(group_ids=None, dateranges=None, subnets=None,
                           invert_group=False, invert_date=False, invert_subnet=False):
    """Fetches a access rule from the database or creates one if not found. The created rule is added to the session.
    group_ids, dateranges and subnets default to None, which finds rules that don't have this value.
    """

    rule = q(AccessRule).filter_by(group_ids=group_ids, dateranges=dateranges, subnets=subnets,
                                   invert_group=invert_group, invert_date=invert_date, invert_subnet=invert_subnet).first()

    if rule is None:
        rule = AccessRule(group_ids=group_ids, dateranges=dateranges, subnets=subnets,
                          invert_group=invert_group, invert_date=invert_date, invert_subnet=invert_subnet)
        db.session.add(rule)

    return rule


def get_all_access_rules(group_ids=None, dateranges=None, subnets=None,
                           invert_group=False, invert_date=False, invert_subnet=False):
    """Fetches all access rules from the database
    """

    rules = q(AccessRule).filter_by(group_ids=group_ids, dateranges=dateranges, subnets=subnets,
                                   invert_group=invert_group, invert_date=invert_date, invert_subnet=invert_subnet).all()

    return rules


def get_or_add_everybody_rule():
    return get_or_add_access_rule()
