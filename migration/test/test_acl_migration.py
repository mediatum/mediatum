# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from core import db
from migration import acl_migration
from sympy import Symbol, S
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


def test_convert_node_rulestrings_to_symbolic_rules_simple(import_node_with_simple_access):
    node = import_node_with_simple_access
    db.session.flush()
    nid_to_rulestr = acl_migration.load_node_rules("readaccess")
    mapper = acl_migration.Mapper()
    nid_to_symbolic_rules = acl_migration.convert_node_rulestrings_to_symbolic_rules(mapper, nid_to_rulestr)
    assert nid_to_symbolic_rules.keys()[0] == node.id
    assert nid_to_symbolic_rules.values()[0] == Symbol("group_test_readers")


def test_convert_node_rulestrings_to_symbolic_rules_predefined_access(import_node_with_predefined_access):
    node = import_node_with_predefined_access
    db.session.flush()
    nid_to_rulestr = acl_migration.load_node_rules("readaccess")
    nid_to_symbolic_rules = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.keys()[0] == node.id
    assert nid_to_symbolic_rules.values()[0] == S("~(group_test_readers | group_test_readers2) | user_darfdas")


def test_convert_node_symbolic_rules_to_access_rules(import_node_with_predefined_access):
    node = import_node_with_predefined_access
    nid_to_symbolic_rule = {node.id: S("~(group_test_readers | group_test_readers2) | user_darfdas")}
    nid_to_access_rules = acl_migration.convert_node_symbolic_rules_to_access_rules(nid_to_symbolic_rule)
    assert nid_to_access_rules.keys()[0] == node.id
    assert nid_to_access_rules.values()[0] == S("~(group_test_readers | group_test_readers2) | user_darfdas")
