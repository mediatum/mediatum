# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core import AccessRule, AccessRuleset, NodeToAccessRule, NodeToAccessRuleset
from core import db
from core.database.postgres import mediatumfunc


def test_access_rules_query(some_node):
    node = some_node
    rr = AccessRule(group_ids=[1])
    rw = AccessRule(group_ids=[2])
    node.access_rule_assocs.append(NodeToAccessRule(rule=rr, ruletype="read"))
    node.access_rule_assocs.append(NodeToAccessRule(rule=rw, ruletype="write", invert=True, blocking=True))
    assert node.access_rule_assocs.filter_by(ruletype="read").one().rule == rr
    assert (node.access_rule_assocs.filter_by(ruletype="write", invert=True, blocking=True).one().rule == rw)


def test_access_get_inherited_access_ruleset_assocs(some_node_with_two_parents):
    node = some_node_with_two_parents
    rs1 = AccessRuleset(name="test", description="fake")
    rs2 = AccessRuleset(name="test2", description="fake2")
    node.parents[0].access_ruleset_assocs.append(NodeToAccessRuleset(ruleset=rs1, ruletype="read"))
    node.parents[1].access_ruleset_assocs.append(NodeToAccessRuleset(ruleset=rs2, ruletype="read"))
    effective_rulesets = [assoc.ruleset for assoc in node.effective_access_ruleset_assocs]
    assert rs1 in effective_rulesets
    assert rs2 in effective_rulesets


def test_access_rule_inheritance_read(some_node_with_two_parents):
    s = db.session
    node = some_node_with_two_parents
    rr1 = AccessRule(group_ids=[1])
    rr2 = AccessRule(group_ids=[2])
    rr3 = AccessRule(group_ids=[3])
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rr1, ruletype="read"))
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rr2, ruletype="read"))
    node.parents[1].access_rule_assocs.append(NodeToAccessRule(rule=rr3, ruletype="read"))
    s.flush()
    f = mediatumfunc.update_inherited_access_rules_for_node(node.id)
    s.execute(f)
    assert node.access_rule_assocs.count() == 3


def test_access_rule_inheritance_write(some_node_with_two_parents):
    s = db.session
    node = some_node_with_two_parents
    rw1 = AccessRule(group_ids=[1])
    rw2 = AccessRule(group_ids=[2])
    rw3 = AccessRule(group_ids=[3])
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rw1, ruletype="write"))
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rw2, ruletype="write"))
    node.parents[1].access_rule_assocs.append(NodeToAccessRule(rule=rw3, ruletype="write"))
    s.flush()
    s.execute(mediatumfunc.update_inherited_access_rules_for_node(node.id))
    assert node.access_rule_assocs.count() == 3
