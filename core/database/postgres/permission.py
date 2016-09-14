# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Integer, Unicode, Boolean, Text, sql, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, CIDR
from sqlalchemy.orm import column_property, object_session

from core.database.postgres import DeclarativeBase, C, rel, integer_pk, TimeStamp, mediatumfunc, FK, dynamic_rel
from core.database.postgres.node import Node
from core.database.postgres.alchemyext import Daterange, map_function_to_mapped_class
from sqlalchemy.dialects.postgresql.constraints import ExcludeConstraint


class AccessRule(DeclarativeBase):
    __tablename__ = "access_rule"
    __versioned__ = {}

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


class AccessRuleset(DeclarativeBase):
    __tablename__ = "access_ruleset"
    __versioned__ = {}

    name = C(Unicode, primary_key=True)
    description = C(Unicode, server_default=u"")


class AccessRulesetToRule(DeclarativeBase):
    __tablename__ = "access_ruleset_to_rule"
    __versioned__ = {}

    rule_id = C(FK(AccessRule.id, ondelete="CASCADE"), primary_key=True, nullable=False)
    ruleset_name = C(FK(AccessRuleset.name, ondelete="CASCADE", onupdate="CASCADE"), primary_key=True, nullable=False)
    invert = C(Boolean, server_default="false", index=True)
    blocking = C(Boolean, server_default="false", index=True)

    rule = rel(AccessRule, backref="ruleset_assocs")


class NodeToAccessRuleset(DeclarativeBase):
    __tablename__ = "node_to_access_ruleset"
    __versioned__ = {}

    nid = C(FK(Node.id, ondelete="CASCADE"), primary_key=True, nullable=False)
    ruleset_name = C(FK(AccessRuleset.name, ondelete="CASCADE", onupdate="CASCADE"), primary_key=True, nullable=False)
    ruletype = C(Text, index=True, primary_key=True, nullable=False)
    invert = C(Boolean, server_default="false", index=True)
    blocking = C(Boolean, server_default="false", index=True)
    private = C(Boolean, server_default="false")

    ruleset = rel(AccessRuleset, backref="node_assocs")

    __table_args__ = (
        # This exclude constraint is something like a unique constraint only for rows where private is true.
        # Postgres doesn't support WHERE for unique constraints (why?), so lets just use this.
        # Alternatively, we could use a unique partial index to enforce the constraint.
        ExcludeConstraint((nid, "="),
                          (ruletype, "="),
                          using="btree",
                          where="private = true",
                          name="only_one_private_ruleset_per_node_and_ruletype"),
        # XXX: missing constraint: private rulesets cannot be used elsewhere if they are private
    )


class IPNetworkList(DeclarativeBase):

    __tablename__ = "ipnetwork_list"
    __versioned__ = {}

    name = C(Unicode, primary_key=True)
    description = C(Unicode)
    subnets = C(ARRAY(CIDR), index=True)


# some Node extensions that could be moved to the Node class later.

Node.access_rule_assocs = dynamic_rel(NodeToAccessRule, backref="node", cascade="all, delete-orphan", passive_deletes=True)
Node.access_ruleset_assocs = dynamic_rel(NodeToAccessRuleset, backref="node", cascade="all, delete-orphan", passive_deletes=True)


def _create_private_ruleset_assoc_for_nid(nid, ruletype):
    ruleset = AccessRuleset(name=u"_{}_{}".format(ruletype, unicode(nid)), description=u"auto-generated")
    ruleset_assoc = NodeToAccessRuleset(nid=nid, ruletype=ruletype, ruleset=ruleset, private=True)
    return ruleset_assoc


def get_or_add_special_access_ruleset(self, ruletype):
    """Gets the special access ruleset for this node for the specified `ruletype`.
    Creates the ruleset if it's missing and adds it to the session.
    Always use this method and don't create private rulesets by yourself!
    :rtype: AccessRuleset
    """

    ruleset_assoc = self.access_ruleset_assocs.filter_by(private=True, ruletype=ruletype).scalar()

    if ruleset_assoc is None:
        # the name doesn't really matter, but it must be unique
        ruleset_assoc = _create_private_ruleset_assoc_for_nid(self.id, ruletype)
        self.access_ruleset_assocs.append(ruleset_assoc)

    ruleset = ruleset_assoc.ruleset
    return ruleset

def get_special_access_ruleset(self, ruletype):
    """Gets the special access ruleset for this node for the specified `ruletype`.
    Returns None, if node has no special ruleset.
    Use Node.get_or_add_special_access_ruleset() instead if you want to edit the special ruleset!
    :rtype: AccessRuleset
    """
    ruleset_assoc = self.access_ruleset_assocs.filter_by(private=True, ruletype=ruletype).scalar()
    if ruleset_assoc is not None:
        return ruleset_assoc.ruleset


Node.get_or_add_special_access_ruleset = get_or_add_special_access_ruleset
Node.get_special_access_ruleset = get_special_access_ruleset


EffectiveNodeToAccessRuleset = map_function_to_mapped_class(mediatumfunc.effective_access_rulesets, NodeToAccessRuleset, "node_id")


def _effective_access_ruleset_assocs(self):
    return object_session(self).query(EffectiveNodeToAccessRuleset).params(node_id=self.id)


Node.effective_access_ruleset_assocs = property(_effective_access_ruleset_assocs)

AccessRuleset.rule_assocs = rel(AccessRulesetToRule, backref="ruleset", cascade="all, delete-orphan", passive_deletes=True)
