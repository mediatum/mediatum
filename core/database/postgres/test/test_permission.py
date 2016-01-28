# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from pytest import raises
from sqlalchemy.exc import IntegrityError
from core.database.postgres.permission import AccessRuleset, NodeToAccessRuleset


def test_get_or_add_private_access_ruleset(some_node):
    read_ruleset = some_node.get_or_add_private_access_ruleset(u"read")
    assert isinstance(read_ruleset, AccessRuleset)
    assert some_node.access_ruleset_assocs.one().private == True

    write_ruleset = some_node.get_or_add_private_access_ruleset(u"write")
    assert some_node.access_ruleset_assocs.count() == 2

    same_ruleset_again = some_node.get_or_add_private_access_ruleset(u"write")
    assert same_ruleset_again is write_ruleset


def test_add_another_private_access_ruleset(session, some_node):
    """Private access rulesets should never be created by hand (use Node.get_or_add_private_access_ruleset).
    But, if you actually do that, this will happen some day:
    """
    with raises(IntegrityError):
        # ok
        some_node.get_or_add_private_access_ruleset(u"read")
        # not ok, someone tries to add a second read private ruleset by hand...
        ruleset = AccessRuleset(name=u"epic_fail")
        ruleset_assoc = NodeToAccessRuleset(ruletype=u"read", ruleset=ruleset, private=True)
        some_node.access_ruleset_assocs.append(ruleset_assoc)
        # flush to enforce constraints
        session.flush()
