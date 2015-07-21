# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from json import dumps
from warnings import warn

import pyaml
from sqlalchemy import (Table, Sequence, Integer, Unicode, Text, sql, text, func, select)
from sqlalchemy.orm import deferred
from sqlalchemy.orm.dynamic import AppenderQuery, AppenderMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property

from core.node import NodeMixin
from core.database.postgres import db_metadata, DeclarativeBase, MtQuery
from core.database.postgres import rel, bref, C, FK
from core.database.postgres.alchemyext import LenMixin, view
from core.database.postgres.attributes import Attributes, AttributesExpressionAdapter
from utils.magicobjects import MInt
from ipaddr import IPv4Address


logg = logging.getLogger(__name__)


class NodeAppenderQuery(AppenderMixin, LenMixin, MtQuery):

    """Custom AppenderQuery class with additional methods for node handling
    """

    def sort_by_orderpos(self, reverse=False):
        if reverse:
            warn("use .order_by(Node.orderpos.desc()) instead", DeprecationWarning)
            return self.order_by(Node.orderpos.desc())
        else:
            warn("use .order_by(Node.orderpos) instead", DeprecationWarning)
            return self.order_by(Node.orderpos)

    def sort_by_name(self, direction="up"):
        reverse = direction != "up"
        if reverse:
            warn("use .order_by(Node.name.desc()) instead", DeprecationWarning)
            return self.order_by(Node.name.desc())
        else:
            warn("use .order_by(Node.name) instead", DeprecationWarning)
            return self.order_by(Node.name)

    def getIDs(self):
        warn("inefficient, rewrite your code using SQLA queries", DeprecationWarning)
        return [n.id for n in self.all()]

    def sort_by_fields(self, field):
        if isinstance(field, str):
            # handle some special cases
            if field == "name" or field == "nodename":
                warn("use query.order_by(Node.name) instead", DeprecationWarning)
                return self.sort_by_name("up")
            elif field == "-name" or field == "nodename":
                warn("use query.order_by(Node.name.desc()) instead", DeprecationWarning)
                return self.sort_by_name("down")
            elif field in ("orderpos", "-orderpos"):
                raise NotImplementedError("this method must not be used for orderpos sorting, use query.order_by(Node.orderpos)!")
            else:
                warn("use query.order_by(Node.attrs[field]).order_by ... instead", DeprecationWarning)
                fields = [field]
        else:
            # remove empty sortfields
            fields = [f for f in field if f]
            if not fields:
                # no fields left, all empty...
                return self
        query = self
        for field in fields:
            if field.startswith("-"):
                expr = Node.attrs[field[1:]].astext.desc()
            else:
                expr = Node.attrs[field].astext
            query = query.order_by(expr)

        return query


t_noderelation = Table("noderelation", db_metadata,
                       C("nid", Integer, FK("node.id"), primary_key=True, index=True),
                       C("cid", Integer, FK("node.id", ondelete="CASCADE"), primary_key=True, index=True),
                       C("distance", Integer, primary_key=True, index=True))


class BaseNodeMeta(DeclarativeMeta):

    def __init__(cls, name, bases, dct):  # @NoSelf
        """Add mapper args with a default polymorphic_identity
        of classname in lowercase if not defined.
        """
        args = dict(polymorphic_identity=cls.__name__.lower())
        if "__mapper_args__" not in cls.__dict__:
            logg.debug("poly identity %s", args)
            cls.__mapper_args__ = args
        super(BaseNodeMeta, cls).__init__(name, bases, dct)


def _cte_subtree(node):
    from core import db

    query = db.query(t_noderelation.c.cid).\
        filter(t_noderelation.c.nid == node.id).\
        distinct().\
        cte(name="subtree")

    return query


def _cte_subtree_container(node):
    from contenttypes.container import Container
    from core import db

    query = db.query(t_noderelation.c.cid).\
        filter(t_noderelation.c.nid == node.id).\
        join(Container, Container.id == t_noderelation.c.cid).\
        distinct().\
        cte(name="subtree")

    return query


# permission check functions for the access types 
access_funcs = {
    "read": func.has_read_access_to_node,
    "write": func.has_write_access_to_node,
    "data": func.has_data_access_to_node
}


class Node(DeclarativeBase, NodeMixin):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"

    id = C(Integer, Sequence('node_id_seq', schema=db_metadata.schema, start=100), primary_key=True)
    type = C(Text, index=True)
    schema = C(Unicode, index=True)
    name = C(Unicode, index=True)
    orderpos = C(Integer, default=1, index=True)
    fulltext = deferred(C(Text))

    attrs = deferred(C(MutableDict.as_mutable(JSONB)))

    @hybrid_property
    def a(self):
        """ see: Attributes"""
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", Attributes(self))
        return self._attributes_accessor

    @a.expression
    def a_expr(self):
        """ see: AttributesExpression"""
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", AttributesExpressionAdapter(self))
        return self._attributes_accessor

    @a.setter
    def a_set(self, value):
        raise NotImplementedError("immutable!")

    def __init__(self, name="", type="node", id=None, schema=None, attrs=None, orderpos=None):
        self.name = name
        if "/" in type:
            warn("use separate type and schema parameters instead of 'type/schema'", DeprecationWarning)
            type, schema = type.split("/")
        self.type = type
        self.attrs = MutableDict()
        if id:
            self.id = id
        if schema:
            self.schema = schema
        if attrs:
            self.attrs.update(attrs)
        if orderpos:
            self.orderpos = orderpos

    @property
    def content_children_for_all_subcontainers(self):
        from contenttypes.data import Content
        from core import db
        subtree = _cte_subtree_container(self)
        query = db.query(Content).\
            join(t_noderelation, Node.id == t_noderelation.c.cid).\
            join(subtree, subtree.c.cid == t_noderelation.c.nid).\
            filter(t_noderelation.c.distance == 1)

        return query

    def all_children_by_query(self, query):
        subtree = _cte_subtree(self)
        query = query.\
            join(subtree, Node.id == subtree.c.cid)
        return query

    @staticmethod
    def req_has_access_to_node_id(node_id, accesstype, req=None, date=func.current_date()):
        from core.transition import request
        from core.users import user_from_session

        if req is None:
            req = request

        user = user_from_session(req.session)
        
        ip = IPv4Address(req.remote_addr)
        return Node.has_access_to_node_id(node_id, accesstype, user, ip, date)

    @staticmethod
    def has_access_to_node_id(node_id, accesstype, user=None, ip=None, date=func.current_date()):
        from core import db
        from core.users import user_from_session
        
        if user.is_admin:
            return True
        
        accessfunc = access_funcs[accesstype]
        group_ids = user.group_ids if user else None
        access = accessfunc(node_id, group_ids, ip, date)
        return db.session.execute(select([access])).scalar()

    __mapper_args__ = {
        'polymorphic_identity': 'node',
        'polymorphic_on': type
    }

    def to_yaml(self):
        """overwrite default DeclarativeBase.to_yaml method because we need to convert MutableDict and MInt first
        """
        as_dict = self.to_dict()
        as_dict["attrs"] = dict(as_dict["attrs"])
        as_dict["id"] = str(as_dict["id"])
        return pyaml.dump(as_dict)


# view for direct parent-child relationship (distance = 1), also used for inserting new node connections
t_nodemapping = view("nodemapping", db_metadata,
                     sql.select([t_noderelation.c.nid, t_noderelation.c.cid]).where(t_noderelation.c.distance == text("1")))

# helpers for node child/parent relationships

_children_rel_options = dict(
    secondary=t_nodemapping,
    lazy="dynamic",
    primaryjoin=Node.id == t_nodemapping.c.nid,
    secondaryjoin=Node.id == t_nodemapping.c.cid,
    query_class=NodeAppenderQuery
)

_all_children_rel_options = dict(
    secondary=t_noderelation,
    lazy="dynamic",
    primaryjoin=Node.id == t_noderelation.c.nid,
    secondaryjoin=Node.id == t_noderelation.c.cid,
    query_class=NodeAppenderQuery,
    viewonly=True
)

_parents_rel_options = dict(
    secondary=t_nodemapping,
    lazy="dynamic",
    primaryjoin=Node.id == t_nodemapping.c.cid,
    secondaryjoin=Node.id == t_nodemapping.c.nid,
    query_class=NodeAppenderQuery
)


def children_rel(*args, **kwargs):
    extended_kwargs = _children_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)


def all_children_rel(*args, **kwargs):
    extended_kwargs = _all_children_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)


def parents_rel(*args, **kwargs):
    extended_kwargs = _parents_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)

# define Node child/parent relationships here

Node.children = children_rel(Node, backref=bref("parents", lazy="dynamic", query_class=NodeAppenderQuery))
Node.all_children = all_children_rel(Node)
