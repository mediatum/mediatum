# -*- coding: utf-8 -*-
"""
    Migrate old-style acl rules to the new Postgres-backend permission system.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
import logging
from pprint import pformat
from ipaddr import IPv4Network
from psycopg2.extras import DateRange
from sympy import Symbol
from sympy.logic import boolalg, Not, And, Or
from sqlalchemy import sql

from core import db, User, UserGroup
from core.database.postgres import mediatumfunc
from core.database.postgres.permission import AccessRule, NodeToAccessRule, AccessRulesetToRule, AccessRuleset, NodeToAccessRuleset
from migration import oldaclparser
from migration.oldaclparser import ACLAndCondition, ACLDateAfterClause, ACLDateBeforeClause, ACLOrCondition, ACLNotCondition,\
    ACLTrueCondition, ACLFalseCondition, ACLGroupCondition, ACLIPCondition, ACLUserCondition, ACLParseException, ACLIPListCondition
from utils.compat import iteritems


q = db.query

logg = logging.getLogger(__name__)


def prepare_acl_rulestring(rulestr):
    return rulestr.replace(",", " OR ").replace("{", "( ").replace("}", " )")


def load_node_rules(ruletype):
    db.session.execute("SET search_path TO mediatum_import")
    expanded_accessrule = mediatumfunc.to_json(mediatumfunc.expand_acl_rule(sql.text(ruletype)))
    stmt = sql.select(["id", expanded_accessrule], from_obj="node").where(sql.text(
        "{} != ''"
        " AND name NOT LIKE 'Arbeitsverzeichnis (%'"
        " AND id IN (SELECT id FROM mediatum.node)".format(ruletype)))

    node_rules = db.session.execute(stmt)
    res = node_rules.fetchall()
    nid_to_rulestr = {r[0]: r[1]["expanded_rule"] for r in res}
    nid_to_rulesets = {r[0]: r[1]["rulesets"] for r in res}
    return nid_to_rulestr, nid_to_rulesets


def convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr, fail_on_first_error=False, ignore_errors=False):
    rulestr_set = set(nid_to_rulestr.itervalues())
    converter = OldACLToBoolExprConverter()
    converter.fail_on_first_error = fail_on_first_error
    rulestr_to_symbolic_rule = converter.batch_convert_rulestrings(rulestr_set)

    if converter.syntax_errors:
        msg = "{} rules failed with syntax error".format(len(converter.syntax_errors))
        if not ignore_errors:
            raise Exception(msg)
        logg.warn(msg)

    if converter.conversion_exceptions:
        msg = "{} rules failed with a conversion error".format(len(converter.conversion_exceptions))
        if not ignore_errors:
            raise Exception(msg)
        logg.warn(msg)

    # map node ids to bool expression results
    nid_to_symbolic_rule = {nid: rulestr_to_symbolic_rule.get(rulestr) for nid, rulestr in nid_to_rulestr.iteritems()}
    return (nid_to_symbolic_rule, converter.symbol_to_acl_cond.copy())


def convert_node_symbolic_rules_to_access_rules(nid_to_symbolic_rule, symbol_to_acl_cond,
                                                fail_on_first_error=False, ignore_errors=False, ignore_missing_user_groups=False):
    converter = SymbolicExprToAccessRuleConverter(symbol_to_acl_cond)
    converter.fail_on_first_error = fail_on_first_error
    symbolic_rule_set = set(nid_to_symbolic_rule.itervalues())
    symbolic_rule_to_access_rules = converter.batch_convert_symbolic_rules(symbolic_rule_set)

    if converter.conversion_exceptions:
        msg = "conversion failed for {} rules".format(len(converter.conversion_exceptions))
        if not ignore_errors:
            raise Exception(msg)
        logg.warn(msg)

    if converter.missing_users:
        msg = "missing users: {}".format(converter.missing_users.values())
        if not ignore_missing_user_groups:
            raise Exception(msg)
        logg.warn(msg)

    if converter.missing_groups:
        msg = "missing groups: {}".format(converter.missing_groups.values())
        if not ignore_missing_user_groups:
            raise Exception(msg)
        logg.warn(msg)

    if converter.fake_groups:
        logg.warn("inserted fake group ids for missing groups / users:\n%s", pformat(converter.fake_groups))

    nid_to_access_rules = {nid: symbolic_rule_to_access_rules.get(symbolic_rule) for nid, symbolic_rule in nid_to_symbolic_rule.iteritems()}
    return nid_to_access_rules


def expand_rulestr(rulestr):
    expanded_accessrule = mediatumfunc.to_json(mediatumfunc.expand_acl_rule(rulestr))
    res = db.session.execute(sql.select([expanded_accessrule])).scalar()
    return res["expanded_rule"], res["rulesets"]


def add_blocking_flag_to_access_rules(rulestr, access_rules):
    """
       The old ACL system blocked write access to a node if a "NOT rule" was found at the node or at one of its parents.
       We use the test from the old core.acl module to find out if a rule should be interpreted as 'blocking'
       :type access_rules: a list of (a: AccessRule, invert: bool)
       :return: a list of (a: AccessRule, (invert: bool, blocking: bool))
    """
    if "NOT ( true )" in rulestr or "NOT ( group" in rulestr:
        # only inverted rules can be used as 'blocking'
        return [(a[0], (a[1], a[1])) for a in access_rules]

    return [(a[0], (a[1], False)) for a in access_rules]


def convert_old_acl(rulestr):
    expr_converter = OldACLToBoolExprConverter()
    symbolic = expr_converter.convert_rulestring(rulestr)
    access_rules = SymbolicExprToAccessRuleConverter(expr_converter.symbol_to_acl_cond).convert_symbolic_rule(symbolic)

    return add_blocking_flag_to_access_rules(rulestr, access_rules)


def find_equivalent_access_rule(a):
    return q(AccessRule).filter_by(invert_date=a.invert_date, invert_group=a.invert_group, invert_subnet=a.invert_subnet,
                                   group_ids=a.group_ids, subnets=a.subnets, dateranges=a.dateranges).scalar()


def convert_symbolic_rules_to_dnf(nid_to_symbolic_rule, simplify=False):
    return {nid: boolalg.to_dnf(rule, simplify=simplify) for nid, rule in iteritems(nid_to_symbolic_rule)}


def save_node_to_rule_mappings(nid_to_access_rules, ruletype):
    s = db.session
    node_to_access_rule_it = (
        NodeToAccessRule(
            nid=nid,
            rule=r[0],
            ruletype=ruletype,
            invert=r[1][0],
            blocking=r[1][1]) for nid,
        rules in nid_to_access_rules.items() for r in set(rules))

    s.add_all(node_to_access_rule_it)


def save_node_to_ruleset_mappings(nid_to_rulesets, ruletype):
    s = db.session
    node_to_access_ruleset_it = (
        NodeToAccessRuleset(
            nid=nid,
            ruleset_name=r,
            ruletype=ruletype) for nid,
        ruleset_names in nid_to_rulesets.items() for r in set(ruleset_names) if r is not None)

    s.add_all(node_to_access_ruleset_it)


def migrate_rules(ruletypes=["read", "write", "data"]):
    for ruletype in ruletypes:
        nid_to_rulestr, nid_to_rulesets = load_node_rules(ruletype + "access")
        nid_to_symbolic_rule, symbol_to_acl_condition = convert_node_rulestrings_to_symbolic_rules(nid_to_rulestr, ignore_errors=False,
                                                                                                   fail_on_first_error=True)
        nid_to_access_rules = convert_node_symbolic_rules_to_access_rules(nid_to_symbolic_rule, symbol_to_acl_condition,
                                                                          fail_on_first_error=True, ignore_missing_user_groups=True)

        for nid, access_rules in nid_to_access_rules.iteritems():
            rulestr = nid_to_rulestr[nid]
            nid_to_access_rules[nid] = add_blocking_flag_to_access_rules(rulestr, access_rules)

        save_node_to_rule_mappings(nid_to_access_rules, ruletype)
        save_node_to_ruleset_mappings(nid_to_rulesets, ruletype)


def migrate_access_entries():
    s = db.session
    access = s.execute("select * from mediatum_import.access").fetchall()
    for a in access:
        rulestr = a["rule"]
        ruleset = AccessRuleset(name=a["name"], description=a["description"])
        access_rules = convert_old_acl(rulestr)
        for rule, (invert, blocking) in access_rules:
            if rule.invert_group is None:
                rule.invert_group = False
            if rule.invert_subnet is None:
                rule.invert_subnet = False
            if rule.invert_date is None:
                rule.invert_date = False

            existing_rule = find_equivalent_access_rule(rule)

            if existing_rule:
                rule = existing_rule

            rule_assoc = AccessRulesetToRule(rule=rule, ruleset=ruleset, invert=invert, blocking=blocking)
            s.add(rule_assoc)


class OldACLToBoolExprConverter(object):

    fail_on_first_error = False

    def __init__(self):
        """
        """
        self.syntax_errors = {}
        self.conversion_exceptions = {}
        self.rulestr_to_symbolic_rule = {}
        self.symbol_to_acl_cond = {}

    def sym(self, name, cond, *args):
        symbol = Symbol(name.encode("utf8"), *args)
        self.symbol_to_acl_cond[symbol] = cond
        return symbol

    def convert_acl_tree(self, condition_tree):
        """Convert a acl syntax tree from ACLParser.parse() to a SymPy representation.
        """
        def visit(cond):
            if isinstance(cond, ACLAndCondition):
                return visit(cond.a) & visit(cond.b)

            elif isinstance(cond, ACLOrCondition):
                return visit(cond.a) | visit(cond.b)

            elif isinstance(cond, ACLNotCondition):
                return ~visit(cond.a)

            elif isinstance(cond, ACLTrueCondition):
                return boolalg.true

            elif isinstance(cond, ACLFalseCondition):
                return boolalg.false

            elif isinstance(cond, ACLGroupCondition):
                return self.sym(u"group_" + cond.group, cond)

            elif isinstance(cond, ACLIPCondition):
                return self.sym(u"ip_{}/{}".format(cond.ip, cond.netmask), cond)

            elif isinstance(cond, ACLIPListCondition):
                return self.sym(u"iplist_" + cond.listid, cond)

            elif isinstance(cond, ACLUserCondition):
                return self.sym(u"user_" + cond.name, cond)

            elif isinstance(cond, ACLDateBeforeClause):
                return self.sym(u"before_{}_{}".format(cond.date, cond.end), cond)

            elif isinstance(cond, ACLDateAfterClause):
                return self.sym(u"after_{}_{}".format(cond.date, cond.end), cond)
            else:
                raise Exception("error, unknown condition type: " + cond.__class__.__name__)

        return visit(condition_tree)

    def convert_rulestring(self, rulestr):
        # cached value?
        if rulestr in self.rulestr_to_symbolic_rule:
            return self.rulestr_to_symbolic_rule[rulestr]

        parsed_condtree = oldaclparser.parse(prepare_acl_rulestring(rulestr))
        return self.convert_acl_tree(parsed_condtree)

    def batch_convert_rulestrings(self, rulestrings):
        rulestr_to_symbolic_rule = {}

        for rulestr in rulestrings:
            if rulestr not in rulestr_to_symbolic_rule:
                try:
                    boolex = self.convert_rulestring(rulestr)

                except ACLParseException as e:
                    if self.fail_on_first_error:
                        raise
                    self.syntax_errors[rulestr] = e

                except Exception as e:
                    if self.fail_on_first_error:
                        raise
                    self.conversion_exceptions[rulestr] = e

                else:
                    rulestr_to_symbolic_rule[rulestr] = boolex

        return rulestr_to_symbolic_rule


def make_open_daterange_from_rule(acl_cond):
    dt = datetime.datetime.strptime(acl_cond.date, "%d.%m.%Y").date()
    if isinstance(acl_cond, ACLDateBeforeClause):
        bounds = "(]" if acl_cond.end else "()"
        return DateRange(datetime.date.min, dt, bounds)
    else:
        bounds = "()" if acl_cond.end else "[)"
        return DateRange(dt, datetime.date.max, bounds)


def make_ipnetwork_from_rule(acl_cond):
    return IPv4Network("{}/{}".format(acl_cond.ip, acl_cond.netmask))


class SymbolicExprToAccessRuleConverter(object):

    fail_on_first_error = False

    def __init__(self, symbol_to_acl_cond):
        self.conversion_exceptions = {}
        # true means access for everybody, so a tuple with a match-all rule is returned
        # false means no access, so a inverted match-all rule is returned
        match_all_rule = AccessRule()
        self.symbolic_rule_to_access_rules = {boolalg.false: ((match_all_rule, True), ),
                                              boolalg.true: ((match_all_rule, False), )}
        self.symbol_to_acl_cond = symbol_to_acl_cond
        self.missing_users = {}
        self.missing_groups = {}
        self.fake_groups = {}

    def get_user_id_from_cond(self, acl_cond):
        username = acl_cond.name
        user = q(User).filter_by(login_name=username).first()
        if not user:
            logg.warn("user %s not found", username)
            self.missing_users[acl_cond] = username
            return self._fake_groupid(username)
        return user.id

    def _fake_groupid(self, name):
        if name in self.fake_groups:
            return self.fake_groups[name]
        else:
            next_groupid = max(self.fake_groups.values()) + 1 if self.fake_groups else 99990000
            self.fake_groups[name] = next_groupid
            return next_groupid

    def get_group_id_from_cond(self, acl_cond):
        groupname = acl_cond.group
        group = q(UserGroup).filter_by(name=groupname).first()
        if not group:
            logg.warn("group %s not found", groupname)
            self.missing_groups[acl_cond] = groupname
            return self._fake_groupid(groupname)
        return group.id

    def rule_model_from_acl_cond(self, acl_cond):
        if isinstance(acl_cond, ACLGroupCondition):
            group_id = self.get_group_id_from_cond(acl_cond)
            return AccessRule(group_ids=set([group_id]))

        elif isinstance(acl_cond, ACLUserCondition):
            user_id = self.get_user_id_from_cond(acl_cond)
            return AccessRule(group_ids=set([user_id]))

        elif isinstance(acl_cond, ACLIPCondition):
            subnet = make_ipnetwork_from_rule(acl_cond)
            return AccessRule(subnets=set([subnet]))

        elif isinstance(acl_cond, ACLIPListCondition):
            # TODO: iplist
            #         subnet = IPv4Network(acl_cond.ip + "/32")
            logg.warn("fake iplist for %s", acl_cond.listid)
            subnet = IPv4Network("127.0.0.0/8")
            return AccessRule(subnets=[subnet])

        elif isinstance(acl_cond, (ACLDateBeforeClause, ACLDateAfterClause)):
            daterange = make_open_daterange_from_rule(acl_cond)
            return AccessRule(dateranges=set([daterange]))

        else:
            raise Exception("!?")

    def get_acl_cond_for_literal(self, cond):
        if isinstance(cond, Not):
            acl_cond = self.symbol_to_acl_cond[cond.args[0]]
            invert = True
        else:
            acl_cond = self.symbol_to_acl_cond[cond]
            invert = False

        return acl_cond, invert

    def convert_symbolic_rule(self, cond):
        # cached value? boolalg.true and boolalg.false are always returned from here
        if cond in self.symbolic_rule_to_access_rules:
            logg.info("convert: known rule: %s", cond)
            return self.symbolic_rule_to_access_rules[cond]

        if boolalg.is_literal(cond):
            acl_cond, invert = self.get_acl_cond_for_literal(cond)
            return ((self.rule_model_from_acl_cond(acl_cond), invert), )

        else:
            access_rules = []
            group_ids = set()
            subnets = set()
            dateranges = set()
            invert_group = False
            invert_subnet = False
            invert_date = False
            invert_access_rule = True if isinstance(cond, Not) else False

            def check_inversion(invert_flag, inversion_state):
                if not invert_flag and inversion_state:
                    raise Exception("cannot be represented: {}".format(cond))
                return invert_flag

            if cond.func is And:
                print "And found"
                cond = Or(*(Not(a) for a in cond.args))
                invert_access_rule = True

            for arg in cond.args:
                if arg.func is And:
                    access_rules.extend(self.convert_symbolic_rule(arg))
                else:
                    acl_cond, invert = self.get_acl_cond_for_literal(arg)

                    if isinstance(acl_cond, ACLGroupCondition):
                        invert_group = check_inversion(invert, invert_group)
                        group_id = self.get_group_id_from_cond(acl_cond)
                        group_ids.add(group_id)

                    if isinstance(acl_cond, ACLUserCondition):
                        invert_group = check_inversion(invert, invert_group)
                        user_id = self.get_user_id_from_cond(acl_cond)
                        group_ids.add(user_id)

                    elif isinstance(acl_cond, ACLIPCondition):
                        invert_subnet = check_inversion(invert, invert_subnet)
                        subnet = make_ipnetwork_from_rule(acl_cond)
                        subnets.add(subnet)

                    elif isinstance(acl_cond, ACLIPListCondition):
                        invert_subnet = check_inversion(invert, invert_subnet)
                        # TODO: iplist
#                         subnet = IPv4Network(acl_cond.iplist + "/32")
                        logg.warn("fake iplist for %s", acl_cond.listid)
                        subnet = IPv4Network("127.0.0.0/8")
                        subnets.add(subnet)

                    elif isinstance(acl_cond, (ACLDateAfterClause, ACLDateBeforeClause)):
                        invert_date = check_inversion(invert, invert_date)
                        daterange = make_open_daterange_from_rule(acl_cond)
                        dateranges.add(daterange)

        access_rules.append((AccessRule(
            group_ids=group_ids or None, dateranges=dateranges or None, subnets=subnets or None, invert_group=invert_group,
            invert_subnet=invert_subnet, invert_date=invert_date),
            invert_access_rule))

        return tuple(access_rules)

    def batch_convert_symbolic_rules(self, symbolic_rules):
        symbolic_rule_to_access_rules = {}

        for symbolic_rule in symbolic_rules:
            if symbolic_rule not in symbolic_rule_to_access_rules:
                try:
                    access_rules = self.convert_symbolic_rule(symbolic_rule)

                except Exception as e:
                    if self.fail_on_first_error:
                        raise
                    self.conversion_exceptions[symbolic_rule] = e

                else:
                    symbolic_rule_to_access_rules[symbolic_rule] = access_rules
            else:
                logg.info("batch: known rule: %s", symbolic_rule)

        return symbolic_rule_to_access_rules
