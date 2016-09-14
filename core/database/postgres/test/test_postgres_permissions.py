# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.database.postgres.permission import AccessRule, AccessRuleset, AccessRulesetToRule


# test DB triggers that must update the access_rule table if access_ruleset_to_rule changes

def test_add_rules_to_node_special_ruleset(session, some_node):
    node = some_node
    srs = node.get_or_add_special_access_ruleset(u"read")
    r1 = AccessRule(group_ids=[1])
    srs.rule_assocs.append(AccessRulesetToRule(rule=r1))
    assert node.access_rule_assocs.first().rule is r1
    r2 = AccessRule(group_ids=[2])
    srs.rule_assocs.append(AccessRulesetToRule(rule=r2, blocking=True, invert=True))
    # check ruleset association
    nar2 = node.access_ruleset_assocs.first()
    assert nar2.ruleset is srs
    assert nar2.private == True
    # check rule association
    arr2 = node.access_rule_assocs[1]
    assert arr2.rule is r2
    assert arr2.ruletype == u"read"
    assert arr2.blocking == True
    assert arr2.invert == True


def test_delete_rule_from_node_special_ruleset(session, some_node):
    node = some_node
    q = session.query
    srs = node.get_or_add_special_access_ruleset(u"read")
    ruleset_name = srs.name
    r1 = AccessRule(group_ids=[1])
    arr = AccessRulesetToRule(rule=r1)
    srs.rule_assocs.append(arr)
    session.flush()
    srs.rule_assocs.remove(arr)
    assert node.access_rule_assocs.count() == 0
    # trigger should remove the special ruleset because it's empty now
    session.expunge_all()
    assert q(AccessRuleset).get(ruleset_name) is None