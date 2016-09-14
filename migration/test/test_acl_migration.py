# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
from ipaddr import IPv4Network
from psycopg2._range import DateRange
import pytest
from pytest import raises, fixture
import sympy
from sympy import Symbol, S

from core import db
from core.database.postgres.permission import AccessRule, NodeToAccessRule, NodeToAccessRuleset, AccessRuleset
from migration import acl_migration
from migration.oldaclparser import ACLGroupCondition
from migration.test.asserts import assert_access_rule, assert_access_rule_with_flags
from migration.acl_migration import convert_symbolic_rules_to_dnf, convert_old_acl, CannotRepresentRule, migrate_rules
from migration.test.factories import AccessRulesetFactory
from core.database.postgres.alchemyext import disable_triggers, enable_triggers, disabled_triggers
from core.test.factories import UserGroupFactory, UserFactory
from migration.test.fixtures import users_and_groups_for_ruleset


acl_migration.OldACLToBoolExprConverter.fail_on_first_error = True
acl_migration.SymbolicExprToAccessRuleConverter.fail_on_first_error = True


def test_load_node_rules_simple_readaccess(session, import_node_with_simple_access):
    node = import_node_with_simple_access
    session.flush()
    _, nid_to_special_rulestrings = acl_migration.load_node_rules("readaccess")
    assert len(nid_to_special_rulestrings) == 1
    assert nid_to_special_rulestrings.keys()[0] == node.id
    assert nid_to_special_rulestrings.values()[0][0] == node.readaccess


def test_load_node_rules_simple_writeaccess(session, import_node_with_simple_access):
    node = import_node_with_simple_access
    session.flush()
    _, nid_to_special_rulestrings = acl_migration.load_node_rules("writeaccess")
    assert len(nid_to_special_rulestrings) == 1
    assert nid_to_special_rulestrings.keys()[0] == node.id
    assert nid_to_special_rulestrings.values()[0][0] == node.writeaccess


def test_load_node_rules_simple_dataaccess(session, import_node_with_simple_access):
    node = import_node_with_simple_access
    session.flush()
    _, nid_to_special_rulestrings = acl_migration.load_node_rules("dataaccess")
    assert len(nid_to_special_rulestrings) == 1
    assert nid_to_special_rulestrings.keys()[0] == node.id
    assert nid_to_special_rulestrings.values()[0][0] == node.dataaccess


test_rulestr_replaced = "NOT ( group test_readers OR group test_readers2 ),{ user darfdas }"


def test_load_node_rules_ruleset(session, import_node_with_non_dnf_ruleset):
    node = import_node_with_non_dnf_ruleset
    session.flush()
    nid_to_rulesets, nid_to_special_rulestrings = acl_migration.load_node_rules("readaccess")
    assert nid_to_rulesets.values()[0] == ["not_rule"]
    assert len(nid_to_special_rulestrings) == 1
    assert nid_to_special_rulestrings[node.id][0] == u"{ user darfdas }"


def test_load_node_rules_stupid_commas_in_readaccess(session, import_node_with_stupid_commas_in_readaccess):
    node = import_node_with_stupid_commas_in_readaccess
    session.flush()
    nid_to_rulesets, nid_to_special_rulestrings = acl_migration.load_node_rules("readaccess")
    expected_ruleset, expected_special_rulestr  = node.readaccess.strip(", ").split(",")
    assert len(nid_to_special_rulestrings) == 1
    assert len(nid_to_rulesets) == 1
    assert nid_to_special_rulestrings.keys()[0] == node.id
    assert nid_to_special_rulestrings.values()[0][0] == expected_special_rulestr
    assert nid_to_rulesets.values()[0][0] == expected_ruleset


def test_convert_node_rulestrings_to_symbolic_rules_true():
    nid_to_rulestr = {1: "( true )"}
    nid_to_symbolic_rules, _ = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.values()[0] is sympy.boolalg.true


### literals

def test_convert_old_acl_group():
    rulestr = "( group x )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000])

def test_convert_old_acl_ip():
    rulestr = "( ip 1.2.3.4 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, subnets=[IPv4Network("1.2.3.4/32")])


def test_convert_old_acl_ip_with_netmask():
    rulestr = "( ip 1.2.3.0/24 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, subnets=[IPv4Network("1.2.3.0/24")])


def test_convert_old_acl_date_later():
    rulestr = "( date > 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=[DateRange(datetime.date(2015, 1, 1), datetime.date(9999, 12, 31), '()')])


def test_convert_old_acl_date_later_inc():
    rulestr = "( date >= 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=[DateRange(datetime.date(2015, 1, 1), datetime.date(9999, 12, 31), '[)')])


def test_convert_old_acl_date_earlier():
    rulestr = "( date < 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=[DateRange(datetime.date(1, 1, 1), datetime.date(2015, 1, 1), '()')])


def test_convert_old_acl_date_earlier_inc():
    rulestr = "( date <= 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False,
                                  dateranges=[DateRange(datetime.date(1, 1, 1), datetime.date(2015, 1, 1), '(]')])

### conjunction

def test_convert_old_acl_group_and_date():
    rulestr = "( group x ) AND ( date > 01.01.2015 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000],
                                  dateranges=[DateRange(datetime.date(2015, 1, 1), datetime.date(9999, 12, 31), '()')])


def test_convert_old_acl_group_and_iplist(some_iplist):
    iplist = some_iplist
    rulestr = "( group x ) AND ( iplist {} )".format(iplist.name)
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000], subnets=iplist.subnets)


def test_convert_old_acl_group_and_ip():
    rulestr = "( group x ) AND ( ip 1.1.1.1 )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000],
                                  subnets=[IPv4Network("1.1.1.1/32")])


@pytest.mark.parametrize("rulestr", [
    "( group x ) AND ( group y )",
    "( group x ) AND ( user y )",
    "( user x ) AND ( user y )",
    "( ip 1.1.1.1 ) AND ( iplist test )",
    "( ip 1.1.1.1 ) AND ( ip 1.2.3.4 )",
    "( iplist test ) AND ( iplist test2 )",
    "( date > 01.01.2015 ) AND ( date < 01.01.2013 )",
    "( group x ) AND ( ( ip 1.1.1.1 ) OR ( date > 01.01.2015 ) )"
])
def test_convert_old_acl_illegal_and_combinations_fail(rulestr):
    with raises(CannotRepresentRule):
        convert_old_acl(rulestr)

### disjunction

def test_convert_old_acl_or():
    rulestr = "( group x ) OR ( group y )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000, 99990001])

def test_convert_old_acl_or_nested_and_not():
    rulestr = "( ( user test ) ) OR ( NOT ( group x ) AND ( NOT ( group y ) ) )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 2
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True, group_ids=[99990001, 99990002])
    assert_access_rule_with_flags(access_rules[1], invert=False, blocking=False, group_ids=[99990000])


def test_or_not_mixed_split_not():
    rulestr = "( NOT ( ip 1.1.1.1 ) OR ( ( group x ) ) )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 2
    assert_access_rule_with_flags(access_rules[1], invert=True, blocking=False, subnets=[IPv4Network("1.1.1.1/32")])
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000])


def test_or_not_mixed_split_2not():
    rulestr = "( NOT ( group x ) OR ( NOT (  ip 1.1.1.1 ) ) )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 2
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True, group_ids=[99990000])
    assert_access_rule_with_flags(access_rules[1], invert=True, blocking=True, subnets=[IPv4Network("1.1.1.1/32")])


def test_or_not_same_split():
    rulestr = "( NOT ( group x ) ) OR ( user y )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 2
    assert_access_rule_with_flags(access_rules[1], invert=True, blocking=True, group_ids=[99990001])
    assert_access_rule_with_flags(access_rules[0], invert=False, blocking=False, group_ids=[99990000])


@pytest.mark.parametrize("old_acl", [
    #"( group x ) OR ( NOT ( user y ) )",
    #"( NOT ( iplist x ) ) OR ( ip 1.1.1.1 )",
    #"( NOT ( date < 01.01.2015 ) ) OR ( date > 01.01.2016 )",
    #"( NOT ( group x ) ) OR ( NOT ( user y ) )",
    "( group x ) AND ( user Y )",
    "( ( user test ) ) OR ( ( user test2 ) AND ( NOT ( group x ) AND ( NOT ( group y ) ) ) )"
])
def test_illegal_or_not_combination_fail(old_acl):
    with raises(CannotRepresentRule):
        convert_old_acl(old_acl)

### outer NOT

def test_convert_old_acl_nobody_rule():
    rulestr = "NOT ( true )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True)


def test_convert_old_acl_not_group_rule():
    rulestr = "NOT ( group hanswurst )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True, group_ids=[99990000])


@pytest.mark.parametrize("old_acl", [
    "NOT ( ( group x ) OR ( user y ) )", # rewrite as: ( NOT ( group x ) ) AND ( NOT ( user y ) )
    "NOT ( ( group x ) AND ( user y ) )",
    "NOT ( ( group x ) OR ( ip 1.1.1.1 ) )",
    "NOT ( ( group x ) AND ( ip 1.1.1.1 ) )",
])
def test_illegal_not_no_literal_fail(old_acl):
    with raises(CannotRepresentRule):
        convert_old_acl(old_acl)

### nested special cases

def test_convert_old_acl_and_2not():
    rulestr = "( NOT ( group x ) ) AND ( NOT ( group y ) )"
    access_rules = convert_old_acl(rulestr)
    assert len(access_rules) == 1
    assert_access_rule_with_flags(access_rules[0], invert=True, blocking=True, group_ids=[99990000, 99990001])


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


def test_convert_node_rulestrings_to_symbolic_rules_ruleset(import_node_with_non_dnf_ruleset):
    node = import_node_with_non_dnf_ruleset
    db.session.flush()
    nid_to_rulestr = {node.id: test_rulestr_replaced}
    nid_to_symbolic_rules, symbol_to_acl_cond = acl_migration.convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr)
    assert nid_to_symbolic_rules.keys()[0] == node.id
    assert nid_to_symbolic_rules.values()[0] == S("~(group_test_readers | group_test_readers2) | user_darfdas")
    assert len(symbol_to_acl_cond) == 3


def test_convert_node_symbolic_rules_to_access_rules(session, import_node_with_non_dnf_ruleset, users_and_groups_for_ruleset):
    node = import_node_with_non_dnf_ruleset
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
    assert_access_rule(access_rules[0][0], group_ids=[g.id for g in groups])
    assert_access_rule(access_rules[1][0], group_ids=[user.get_or_add_private_group().id])


# def test_save_node_to_rule_mappings(two_access_rules, some_numbered_nodes, session):
#     rule1, rule2 = two_access_rules
#     db.session.flush()  # we need to flush the nodes first to set their ids
#     nid_to_access_rules = {1: [(rule1, (True, False)), (rule2, (True, False))],
#                            2: [(rule1, (True, False))],
#                            3: [(rule2, (True, False))]}
#     acl_migration.save_node_to_rule_mappings(nid_to_access_rules, "read")
#     assert session.query(AccessRule).count() == 2
#     assert session.query(NodeToAccessRule).count() == 4
#     assert some_numbered_nodes[0].access_rule_assocs.count() == 2


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


def test_convert_nid_to_rulestr(import_node_with_non_dnf_ruleset):
    nid_to_rulestr = {1: "{ NOT ( group z ) }",
                      2: "{ group x },{ group y }",
                      3: ""}

    nid_to_access_rules = acl_migration.convert_nid_to_rulestr(nid_to_rulestr)
    assert len(nid_to_access_rules) == 3
    assert len(nid_to_access_rules[1]) == 1
    assert len(nid_to_access_rules[2]) == 1
    assert len(nid_to_access_rules[3]) == 0
    assert_access_rule_with_flags(nid_to_access_rules[1][0], group_ids=[99990000], invert=True, blocking=True)
    assert_access_rule_with_flags(nid_to_access_rules[2][0], group_ids=[99990001, 99990002], invert=False, blocking=False)


def test_migrate_rules(session, import_node_with_ruleset, ruleset, users_and_groups_for_ruleset):
    import_node = import_node_with_ruleset
    from core import Node
    session.flush()

    with disabled_triggers():
        migrate_rules()
        session.flush()

    node = session.query(Node).get(import_node.id)
    access_rules = [ra.rule for ra in node.access_rule_assocs]
    private_access_ruleset = node.get_or_add_special_access_ruleset(u"read")
    assert len(private_access_ruleset.rule_assocs) == 1
    assert private_access_ruleset.rule_assocs[0].rule in access_rules
    assert node.access_ruleset_assocs.filter_by(ruleset_name=ruleset.name, ruletype=u"read").scalar()
    assert len(access_rules) == 2
