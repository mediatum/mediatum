# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Integer, Unicode, Boolean, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY, CIDR

from core.database.postgres import DeclarativeBase, C, FK, db_metadata, rel, integer_pk, integer_fk, TimeStamp
from core.database.postgres.node import Node
from core.database.postgres.alchemyext import Daterange


class AccessRule(DeclarativeBase):
    __tablename__ = "access_rule"

    id = integer_pk()
    name = C(Unicode, index=True)
    blocking = C(Boolean, default=False, index=True)
    invert_subnet = C(Boolean, default=False, index=True)
    invert_date = C(Boolean, default=False, index=True)
    invert_group = C(Boolean, default=False, index=True)
    group_ids = C(ARRAY(Integer), index=True)
    subnets = C(ARRAY(CIDR), index=True)
    dateranges = C(ARRAY(Daterange), index=True)
    inherited = C(Boolean, default=False, index=True)


class NodeToAccessRule(DeclarativeBase):
    __tablename__ = "node_to_access_rule"

    nid = integer_fk(Node.id, primary_key=True)
    rule_id = integer_fk(AccessRule.id, primary_key=True)
    ruletype = C(Text, index=True)
    invert = C(Boolean, default=False, index=True)
    inherited = C(Boolean, default=False, index=True)

    rule = rel(AccessRule, backref="node_assocs")

Node.access_rules = rel(NodeToAccessRule, backref="node")