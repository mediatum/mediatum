# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Integer, Unicode, Boolean, Text, sql
from sqlalchemy.dialects.postgresql import ARRAY, CIDR

from core.database.postgres import DeclarativeBase, C, rel, integer_pk, TimeStamp, mediatumfunc, FK, dynamic_rel
from core.database.postgres.node import Node
from core.database.postgres.alchemyext import Daterange, map_function_to_mapped_class
from sqlalchemy.orm import column_property, object_session


class AccessRule(DeclarativeBase):
    __tablename__ = "access_rule"

    id = integer_pk()
    invert_subnet = C(Boolean, server_default="false", index=True)
    invert_date = C(Boolean, server_default="false", index=True)
    invert_group = C(Boolean, server_default="false", index=True)
    group_ids = C(ARRAY(Integer), index=True)
    subnets = C(ARRAY(CIDR), index=True)
    dateranges = C(ARRAY(Daterange), index=True)

    group_names = column_property(mediatumfunc.group_ids_to_names(sql.text("group_ids")))


class NodeToAccessRule(DeclarativeBase):
    __tablename__ = "node_to_access_rule"

    nid = C(FK(Node.id, ondelete="CASCADE"), primary_key=True)
    rule_id = C(FK(AccessRule.id, ondelete="CASCADE"), primary_key=True)
    ruletype = C(Text, index=True, primary_key=True)
    invert = C(Boolean, server_default="false", index=True, primary_key=True)
    inherited = C(Boolean, server_default="false", index=True)
    blocking = C(Boolean, server_default="false", index=True, primary_key=True)

    rule = rel(AccessRule, backref="node_assocs")


class AccessRuleset(DeclarativeBase, TimeStamp):
    __tablename__ = "access_ruleset"

    name = C(Unicode, primary_key=True)
    description = C(Unicode, server_default="''")


class AccessRulesetToRule(DeclarativeBase):
    __tablename__ = "access_ruleset_to_rule"

    rule_id = C(FK(AccessRule.id), primary_key=True)
    ruleset_name = C(FK(AccessRuleset.name, ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    invert = C(Boolean, server_default="false", index=True)
    blocking = C(Boolean, server_default="false", index=True)

    rule = rel(AccessRule, backref="ruleset_assocs")


class NodeToAccessRuleset(DeclarativeBase):
    __tablename__ = "node_to_access_ruleset"

    nid = C(FK(Node.id, ondelete="CASCADE"), primary_key=True, nullable=False)
    ruleset_name = C(FK(AccessRuleset.name, ondelete="CASCADE", onupdate="CASCADE"), primary_key=True, nullable=False)
    ruletype = C(Text, index=True, primary_key=True, nullable=False)
    invert = C(Boolean, server_default="false", index=True)
    blocking = C(Boolean, server_default="false", index=True)

    ruleset = rel(AccessRuleset, backref="node_assocs")


Node.access_rule_assocs = dynamic_rel(NodeToAccessRule, backref="node", cascade="all, delete-orphan", passive_deletes=True)
Node.access_ruleset_assocs = dynamic_rel(NodeToAccessRuleset, backref="node", cascade="all, delete-orphan", passive_deletes=True)


EffectiveNodeToAccessRuleset = map_function_to_mapped_class(mediatumfunc.effective_access_rulesets, NodeToAccessRuleset, "node_id")


def _effective_access_ruleset_assocs(self):
    return object_session(self).query(EffectiveNodeToAccessRuleset).params(node_id=self.id)


Node.effective_access_ruleset_assocs = property(_effective_access_ruleset_assocs)

AccessRuleset.rule_assocs = rel(AccessRulesetToRule, backref="ruleset")
