# -*- coding: utf-8 -*-
"""
    Migrate old-style acl rules to the new Postgres-backend permission system.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
import logging
from ipaddr import IPv4Network
from psycopg2.extras import DateRange
from sympy import Symbol
from sympy.logic import boolalg, Not, And, Or
from sqlalchemy import sql

from core import db
from core.database.postgres.permission import AccessRule, NodeToAccessRule
from core import User, UserGroup
from migration import oldaclparser
from migration.oldaclparser import ACLAndCondition, ACLDateAfterClause, ACLDateBeforeClause , ACLOrCondition, ACLNotCondition,\
    ACLTrueCondition, ACLFalseCondition, ACLGroupCondition, ACLIPCondition, ACLUserCondition, ACLParseException, ACLIPListCondition
from utils.compat import iteritems

q = db.query

logg = logging.getLogger(__name__)

PL_FUNC_EXPAND_ACL_RULE = """

CREATE OR REPLACE FUNCTION mediatum_import.expand_acl_rule(rulestr text)
  RETURNS text AS
$BODY$
DECLARE
    expanded_rule text;
BEGIN
SELECT array_to_string(array_agg((
    SELECT CASE
        WHEN n LIKE '{%' THEN n
        ELSE (SELECT rule FROM access WHERE name = n)
        END
        )),',')
    
INTO expanded_rule
FROM unnest(regexp_split_to_array(rulestr, ',')) AS n;
RETURN expanded_rule;
END;
$BODY$
  LANGUAGE plpgsql STABLE
  COST 100;
"""


def prepare_acl_rulestring(rulestr):
    return rulestr.replace(",", " OR ").replace("{", "( ").replace("}", " )")


def load_node_rules(ruletype):
    db.session.execute("SET search_path TO mediatum_import")
    stmt = sql.select(["id", sql.func.expand_acl_rule(sql.text(ruletype)).label(ruletype)], from_obj="node") \
        .where(sql.func.expand_acl_rule(sql.text(ruletype)) != "")

    node_rules = db.session.execute(stmt)
    # map node id to rulestring
    return dict(node_rules.fetchall())


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


def convert_node_symbolic_rules_to_access_rules(nid_to_symbolic_rule, symbol_to_acl_cond, fail_on_first_error=False, ignore_errors=False):
    converter = SymbolicExprToAccessRuleConverter(symbol_to_acl_cond)
    converter.fail_on_first_error = fail_on_first_error
    symbolic_rule_set = set(nid_to_symbolic_rule.itervalues())
    symbolic_rule_to_access_rules = converter.batch_convert_symbolic_rules(symbolic_rule_set)

    if converter.conversion_exceptions:
        msg = "conversion failed for {} rules".format(len(converter.conversion_exceptions))
        if not ignore_errors:
            raise Exception(msg)
        logg.warn(msg)

    nid_to_access_rules = {nid: symbolic_rule_to_access_rules.get(symbolic_rule) for nid, symbolic_rule in nid_to_symbolic_rule.iteritems()}
    return nid_to_access_rules


def convert_symbolic_rules_to_dnf(nid_to_symbolic_rule, simplify=False):
    return {nid: boolalg.to_dnf(rule, simplify=simplify) for nid, rule in iteritems(nid_to_symbolic_rule)}


def save_access_rules(nid_to_access_rules, ruletype):
    node_to_access_rule_it = (
        NodeToAccessRule(
            nid=nid,
            rule=r[0],
            ruletype=ruletype,
            invert=r[1]) for nid,
        rules in nid_to_access_rules.items() for r in rules)
    db.session.add_all(node_to_access_rule_it)


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
                return self.sym(u"ip_" + cond.ip, cond)

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
        bounds = "[)" if acl_cond.end else "()"
        return DateRange(dt, datetime.date.max, bounds)


def rule_model_from_acl_cond(acl_cond):
    if isinstance(acl_cond, ACLGroupCondition):
        group = q(UserGroup).filter_by(name=acl_cond.group).first()
        return AccessRule(group_ids=[group.id])

    elif isinstance(acl_cond, ACLUserCondition):
        user = q(User).filter_by(login_name=acl_cond.name).first()
        user_id = user.id if user is not None else 9999999
        return AccessRule(group_ids=[user_id])

    elif isinstance(acl_cond, ACLIPCondition):
        subnet = IPv4Network(acl_cond.ip + "/32")
        return AccessRule(subnets=[subnet])

    elif isinstance(acl_cond, ACLIPListCondition):
        # TODO: iplist
        #         subnet = IPv4Network(acl_cond.ip + "/32")
        logg.warn("fake iplist for %s", acl_cond.listid)
        subnet = IPv4Network("127.0.0.0/8")
        return AccessRule(subnets=[subnet])

    elif isinstance(acl_cond, (ACLDateBeforeClause, ACLDateAfterClause)):
        daterange = make_open_daterange_from_rule(acl_cond)
        return AccessRule(dateranges=[daterange])

    else:
        raise Exception("!?")


class SymbolicExprToAccessRuleConverter(object):

    fail_on_first_error = False

    def __init__(self, symbol_to_acl_cond):
        self.conversion_exceptions = {}
        # false means no access, so an empty tuple is returned
        # true means access for everybody, so a tuple with a match-all rule is returned
        self.symbolic_rule_to_access_rules = {boolalg.false: tuple(),
                                              boolalg.true: (AccessRule(), )}
        self.symbol_to_acl_cond = symbol_to_acl_cond

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
            return ((rule_model_from_acl_cond(acl_cond), invert))

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
                if invert_flag and not inversion_state:
                    return True
                elif not invert_flag and inversion_state:
                    raise Exception("cannot be represented: {}".format(cond))
                else:
                    return False

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
                        group = q(UserGroup).filter_by(name=acl_cond.group).first()
                        if group is not None:
                            group_ids.add(group.id)

                    if isinstance(acl_cond, ACLUserCondition):
                        invert_group = check_inversion(invert, invert_group)
                        user = q(User).filter_by(login_name=acl_cond.name).first()
                        if user is not None:
                            group_ids.add(user.id)

                    elif isinstance(acl_cond, ACLIPCondition):
                        invert_subnet = check_inversion(invert, invert_subnet)
                        subnet = IPv4Network(acl_cond.ip + "/32")
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
