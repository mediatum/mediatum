# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sympy import Symbol, S

from core import db
from core.database.postgres.permission import AccessRule, NodeToAccessRule
from migration import acl_migration
from migration.oldaclparser import ACLGroupCondition
from migration.test.asserts import assert_access_rule
import sympy
from migration.acl_migration import convert_symbolic_rules_to_dnf


acl_migration.OldACLToBoolExprConverter.fail_on_first_error = True
acl_migration.SymbolicExprToAccessRuleConverter.fail_on_first_error = True


def test_load_node_rules_simple_readaccess(import_node_with_simple_access):
    node = import_node_with_simple_access
    db.session.flush()
    nid_to_rulestr, _ = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == node.readaccess


def test_load_node_rules_simple_writeaccess(import_node_with_simple_access):
    node = import_node_with_simple_access
    db.session.flush()
    nid_to_rulestr, _ = acl_migration.load_node_rules("writeaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == node.writeaccess


test_rulestr_replaced = "NOT ( group test_readers OR group test_readers2 ),{ user darfdas }"


def test_load_node_rules_predefined_access(import_node_with_predefined_access):
    node = import_node_with_predefined_access
    db.session.flush()
    nid_to_rulestr, nid_to_rulesets = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulestr.keys()[0] == node.id
    assert nid_to_rulestr.values()[0] == test_rulestr_replaced
    assert nid_to_rulesets.values()[0] == ["not_rule", None]


def test_convert_node_rulestrings_to_symbolic_rules_true():
    nid_to_rulestr = {1: "( true )"}
    nid_to_symbolic_rules, _ = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.values()[0] is sympy.boolalg.true


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
    # XXX: nid_to_symbolic_rule should be created here instead of using these functions
    nid_to_symbolic_rule, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    
    nid_to_access_rules = acl_migration.convert_node_symbolic_rules_to_access_rules(
        convert_symbolic_rules_to_dnf(nid_to_symbolic_rule),
        symbol_to_acl_cond)
    
    assert nid_to_access_rules.keys()[0] == node.id
    access_rules = nid_to_access_rules.values()[0]
    assert len(access_rules) == 2
    # check inversion flags
    assert access_rules[0][1]
    assert access_rules[1][1] == False
    # check rule contents
    assert_access_rule(access_rules[0][0], group_ids=set([g.id for g in groups]))
    assert_access_rule(access_rules[1][0], group_ids=set([u.id for u in users]))


def test_save_access_rules(two_access_rules, some_numbered_nodes, session):
    rule1, rule2 = two_access_rules
    db.session.flush()  # we need to flush the nodes first to set their ids
    nid_to_access_rules = {1: [(rule1, True), (rule2, False)],
                           2: [(rule1, False)],
                           3: [(rule2, False)]}
    acl_migration.save_access_rules(nid_to_access_rules, "read")
    assert session.query(AccessRule).count() == 2
    assert session.query(NodeToAccessRule).count() == 4
    assert len(some_numbered_nodes[0].access_rules) == 2
