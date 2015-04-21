# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core import db
from migration import acl_migration
from sympy import Symbol, S
from migration.oldaclparser import ACLGroupCondition
from migration.test.asserts import assert_access_rule
acl_migration.OldACLToBoolExprConverter.fail_on_first_exception = True
acl_migration.SymbolicExprToAccessRuleConverter.fail_on_first_exception = True


def test_load_node_rules_simple_readaccess(import_node_with_simple_access):
    node = import_node_with_simple_access
    db.session.flush()
    nid_to_rulestr = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == node.readaccess


def test_load_node_rules_simple_writeaccess(import_node_with_simple_access):
    node = import_node_with_simple_access
    db.session.flush()
    nid_to_rulestr = acl_migration.load_node_rules("writeaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == node.writeaccess


test_rulestr_replaced = "NOT ( group test_readers OR group test_readers2 ),{ user darfdas }"


def test_load_node_rules_predefined_access(import_node_with_predefined_access):
    node = import_node_with_predefined_access
    db.session.flush()
    nid_to_rulestr = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == test_rulestr_replaced


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


def test_convert_node_rulestrings_to_symbolic_rules_predefined_access(import_node_with_predefined_access):
    node = import_node_with_predefined_access
    db.session.flush()
    nid_to_rulestr = {node.id: test_rulestr_replaced}
    nid_to_symbolic_rules, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.keys()[0] == node.id
    assert nid_to_symbolic_rules.values()[0] == S("~(group_test_readers | group_test_readers2) | user_darfdas")
    assert len(symbol_to_acl_cond) == 3


def test_convert_node_symbolic_rules_to_access_rules(import_node_with_predefined_access, users_and_groups_for_predefined_access):
    node = import_node_with_predefined_access
    users, groups = users_and_groups_for_predefined_access
    nid_to_rulestr = {node.id: test_rulestr_replaced}
    nid_to_symbolic_rule, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    nid_to_access_rules = acl_migration.convert_node_symbolic_rules_to_access_rules(nid_to_symbolic_rule, symbol_to_acl_cond)
    assert nid_to_access_rules.keys()[0] == node.id
    access_rules = nid_to_access_rules.values()[0]
    assert len(access_rules) == 2
    # check inversion flags
    assert access_rules[0][1]
    assert access_rules[1][1] == False
    # check rule contents
    assert_access_rule(access_rules[0][0], group_ids=set([g.id for g in groups]))
    assert_access_rule(access_rules[1][0], group_ids=set([u.id for u in users]))
