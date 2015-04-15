# -*- coding: utf-8 -*-
"""
    Migrate old-style acl rules to the new Postgres-backend permission system.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
from ipaddr import IPv4Network
from psycopg2.extras import DateRange
from sympy import Symbol
from sympy.logic import boolalg, Not, And, Or

import core
from core.database.postgres.permission import AccessRule
from core.usergroup import UserGroup
from core.users import getUser
from migration import oldaclparser
from migration.oldaclparser import ACLAndCondition, ACLDateAfterClause, ACLDateBeforeClause , ACLOrCondition, ACLNotCondition,\
    ACLTrueCondition, ACLFalseCondition, ACLGroupCondition, ACLIPCondition, ACLUserCondition, ACLParseException


s = core.db.session
q = s.query


def prepare_acl_rulestring(self, rulestr):
    return rulestr.replace(",", " OR ").replace("{", "( ").replace("}", " )")


class Mapper(object):

    def __init__(self):
        self.symbol_to_acl_condition = {}

    def get_acl_cond_for_literal(self, cond):
        if isinstance(cond, Not):
            acl_cond = self.symbol_to_acl_condition[cond.args[0]]
            invert = True
        else:
            acl_cond = self.symbol_to_acl_condition[cond]
            invert = False
    
        return acl_cond, invert



class OldACLToBoolExprConverter(object):

    def __init__(self, mapper):
        self.mapper = mapper
        self.acl_syntax_errors = {}
        self.conversion_exceptions = {}

    def sym(self, name, cond, *args):
        symbol = Symbol(name.encode("utf8"), *args)
        self.mapper.symbol_to_acl_condition[symbol] = cond
        return symbol

    def convert_rulestring(self, rulestr):
        parsed_condtree = oldaclparser.parse(prepare_acl_rulestring(rulestr))
        return self.convert_acl_tree(parsed_condtree)

    def batch_convert_rulestrings(self, rulestrings):
        bool_exprs = []

        for rulestr in rulestrings:
            try:
                boolex = self.convert_rulestring(rulestr)

            except ACLParseException as e:
                self.acl_syntax_errors[rulestr] = e

            except Exception as e:
                self.conversion_exceptions[rulestr] = e

            bool_exprs.append(boolex)

    def convert_acl_tree(self, condition_tree):
        """Convert a acl syntax tree from ACLParser.parse() to a SymPy representation.
        """
        def visit(cond):
            if isinstance(cond, ACLAndCondition):
                return self.visit(cond.a) & self.visit(cond.b)

            elif isinstance(cond, ACLOrCondition):
                return self.visit(cond.a) | self.visit(cond.b)

            elif isinstance(cond, ACLNotCondition):
                return ~self.visit(cond.a)

            elif isinstance(cond, ACLTrueCondition):
                return boolalg.true

            elif isinstance(cond, ACLFalseCondition):
                return boolalg.false

            elif isinstance(cond, ACLGroupCondition):
                return self.sym(u"group_" + cond.group, cond)

            elif isinstance(cond, ACLIPCondition):
                return self.sym(u"ip_" + cond.ip, cond)

            elif isinstance(cond, ACLUserCondition):
                return self.sym(u"user_" + cond.name, cond)

            elif isinstance(cond, ACLDateBeforeClause):
                return self.sym(u"before_{}_{}".format(cond.date, cond.end), cond)

            elif isinstance(cond, ACLDateAfterClause):
                return self.sym(u"after_{}_{}".format(cond.date, cond.end), cond)

            else:
                raise Exception("error, unknown condition type: " + cond.__class__)

        return visit(condition_tree)


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
        user = getUser(acl_cond.name)
        user_id = user.id if user is not None else 9999999
        return AccessRule(group_ids=[user_id])

    elif isinstance(acl_cond, ACLIPCondition):
        subnet = IPv4Network(acl_cond.ip + "/32")
        return AccessRule(subnets=[subnet])

    elif isinstance(acl_cond, (ACLDateBeforeClause, ACLDateAfterClause)):
        daterange = make_open_daterange_from_rule(acl_cond)
        return AccessRule(dateranges=[daterange])
    else:
        raise Exception("!?")


class SymbolicExprToAccessRuleConverter(object):
    
    def __init__(self, mapper):
        self.mapper = mapper

    def symbolic_rule_to_access_rules(self, cond):
        if boolalg.is_literal(cond):
            acl_cond, invert = self.mapper.get_acl_cond_for_literal(cond)
            return [(rule_model_from_acl_cond(acl_cond), invert)]
    
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
                    access_rules.extend(self.symbolic_rule_to_access_rules(arg))
                else:
                    acl_cond, invert = self.mapper.get_acl_cond_for_literal(arg)
    
                    if isinstance(acl_cond, ACLGroupCondition):
                        invert_group = check_inversion(invert, invert_group)
                        group = q(UserGroup).filter_by(name=acl_cond.group).first()
                        if group is not None:
                            group_ids.add(group.id)
    
                    if isinstance(acl_cond, ACLUserCondition):
                        invert_group = check_inversion(invert, invert_group)
                        user = getUser(acl_cond.name)
                        if user is not None:
                            group_ids.add(user.id)
    
                    elif isinstance(acl_cond, ACLIPCondition):
                        invert_subnet = check_inversion(invert, invert_subnet)
                        subnet = IPv4Network(acl_cond.ip + "/32")
                        subnets.add(subnet)
    
                    elif isinstance(acl_cond, (ACLDateAfterClause, ACLDateBeforeClause)):
                        invert_date = check_inversion(invert, invert_date)
                        daterange = make_open_daterange_from_rule(acl_cond)
                        dateranges.add(daterange)
    
        access_rules.append((AccessRule(
            group_ids=group_ids or None, dateranges=dateranges or None, subnets=subnets or None, invert_group=invert_group,
            invert_subnet=invert_subnet, invert_date=invert_date),
            invert_access_rule))
    
        return access_rules
