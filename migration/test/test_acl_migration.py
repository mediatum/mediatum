# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sympy import Symbol, S

from core import db
from core.database.postgres.permission import AccessRule, NodeToAccessRule, NodeToAccessRuleset, AccessRuleset
from migration import acl_migration
from migration.oldaclparser import ACLGroupCondition
from migration.test.asserts import assert_access_rule, assert_access_rule_with_flags
import sympy
from migration.acl_migration import convert_symbolic_rules_to_dnf, convert_old_acl
from ipaddr import IPv4Network
from psycopg2._range import DateRange
import datetime


acl_migration.OldACLToBoolExprConverter.fail_on_first_error = True
acl_migration.SymbolicExprToAccessRuleConverter.fail_on_first_error = True


def test_load_node_rules_simple_readaccess(session, import_node_with_simple_access):
    node = import_node_with_simple_access
    session.flush()
    nid_to_rulestr, _ = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == node.readaccess


def test_load_node_rules_simple_writeaccess(session, import_node_with_simple_access):
    node = import_node_with_simple_access
    session.flush()
    nid_to_rulestr, _ = acl_migration.load_node_rules("writeaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == node.writeaccess


test_rulestr_replaced = "NOT ( group test_readers OR group test_readers2 ),{ user darfdas }"


def test_load_node_rules_ruleset(session, import_node_with_ruleset):
    node = import_node_with_ruleset
    session.flush()
    nid_to_rulestr, nid_to_rulesets = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == test_rulestr_replaced
    assert nid_to_rulesets.values()[0] == ["not_rule", None]


def test_convert_node_rulestrings_to_symbolic_rules_true():
    nid_to_rulestr = {1: "( true )"}
    nid_to_symbolic_rules, _ = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.values()[0] is sympy.boolalg.true


def test_convert_old_acl_or():
    rulestr = "( group x ) OR ( group y )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=set([99990000, 99990001]))


# XXX: we don't use rules like these, not implemented correctly
# def test_convert_old_acl_or_2not():
#     rulestr = "( NOT ( user test ) ) OR ( NOT ( group x ) )"
#     access_rules = convert_old_acl(rulestr)
#     assert len(access_rules) == 1
#     assert_access_rule_with_flags(access_rules[0], invert=False, blocking=True, group_ids=set([99990000, 99990001]), invert_group=True)


def test_convert_old_acl_ip_with():
    rulestr = "( ip 1.2.3.4 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, subnets=set([IPv4Network("1.2.3.4/32")]))


def test_convert_old_acl_ip_with_netmask():
    rulestr = "( ip 1.2.3.0/24 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, subnets=set([IPv4Network("1.2.3.0/24")]))


def test_convert_old_acl_date_later():
    rulestr = "( date > 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=set([DateRange(datetime.date(2015, 1, 1), datetime.date(9999, 12, 31), '()')]))


def test_convert_old_acl_date_later_inc():
    rulestr = "( date >= 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=set([DateRange(datetime.date(2015, 1, 1), datetime.date(9999, 12, 31), '[)')]))


def test_convert_old_acl_date_earlier():
    rulestr = "( date < 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=set([DateRange(datetime.date(1, 1, 1), datetime.date(2015, 1, 1), '()')]))


def test_convert_old_acl_date_earlier_inc():
    rulestr = "( date <= 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=set([DateRange(datetime.date(1, 1, 1), datetime.date(2015, 1, 1), '(]')]))


def test_convert_old_acl_nobody_rule():
    rulestr = "NOT ( true )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True)


def test_convert_old_acl_not_group_rule():
    rulestr = "NOT ( group hanswurst )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True, group_ids=set([99990000]))


def test_convert_node_rulestrings_to_symbolic_rules_simple(import_node_with_simple_access):
    node = import_node_with_simple_access
    db.session.flush()
    nid_to_rulestr = {node.id: node.readaccess}
    nid_to_symbolic_rules, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.keys()[0] == node.id
    assert nid_to_symbolic_rules.values()[0] == Symbol("group_test_readers")
    assert symbol_to_acl_cond.keys()[0] == Symbol("group_test_readers")
    acl_cond = symbol_to_acl_cond.values()[0]
    assert isinstance(acl_cond, ACLGroupCondition)


def test_convert_node_rulestrings_to_symbolic_rules_ruleset(import_node_with_ruleset):
    node = import_node_with_ruleset
    db.session.flush()
    nid_to_rulestr = {node.id: test_rulestr_replaced}
    nid_to_symbolic_rules, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.keys()[0] == node.id
    assert nid_to_symbolic_rules.values()[0] == S("~(group_test_readers | group_test_readers2) | user_darfdas")
    assert len(symbol_to_acl_cond) == 3


def test_convert_node_symbolic_rules_to_access_rules(session, import_node_with_ruleset, users_and_groups_for_ruleset):
    node = import_node_with_ruleset
    users, groups = users_and_groups_for_ruleset
    user = users[0]
    session.flush()
    nid_to_rulestr = {node.id: test_rulestr_replaced}
    nid_to_symbolic_rule, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)

    nid_to_access_rules = acl_migration.convert_node_symbolic_rules_to_access_rules(
        convert_symbolic_rules_to_dnf(nid_to_symbolic_rule),
        symbol_to_acl_cond)

    assert nid_to_access_rules.keys()[0] == node.id
    access_rules = nid_to_access_rules.values()[0]
    assert len(access_rules) == 2
    # check inversion flag
    assert access_rules[0][1] == True
    # the second rule is the user-based rule
    assert access_rules[1][1] == False
    # check rule contents
    # last group is the private user group
    assert_access_rule(access_rules[0][0], group_ids=set([g.id for g in groups]))
    assert_access_rule(access_rules[1][0], group_ids=set([user.get_or_add_private_group().id]))


def test_save_node_to_rule_mappings(two_access_rules, some_numbered_nodes, session):
    rule1, rule2 = two_access_rules
    db.session.flush()  # we need to flush the nodes first to set their ids
    nid_to_access_rules = {1: [(rule1, (True, False)), (rule2, (True, False))],
                           2: [(rule1, (True, False))],
                           3: [(rule2, (True, False))]}
    acl_migration.save_node_to_rule_mappings(nid_to_access_rules, "read")
    assert session.query(AccessRule).count() == 2
    assert session.query(NodeToAccessRule).count() == 4
    assert some_numbered_nodes[0].access_rule_assocs.count() == 2


def test_save_node_to_ruleset_mappings(two_access_rulesets, some_numbered_nodes, session):
    ruleset1, ruleset2 = two_access_rulesets
    session.add(ruleset1)
    session.add(ruleset2)
    nid_to_access_ruleset_names = {1: [ruleset1.name, ruleset2.name],
                                   2: [ruleset1.name, None],
                                   3: [None]}
    acl_migration.save_node_to_ruleset_mappings(nid_to_access_ruleset_names, "read")
    assert session.query(AccessRuleset).count() == 2
    assert session.query(NodeToAccessRuleset).count() == 3
    rulesets_for_node = [m.ruleset for m in some_numbered_nodes[0].access_ruleset_assocs]
    assert len(rulesets_for_node) == 2
    assert ruleset1 in rulesets_for_node
    assert ruleset2 in rulesets_for_node
