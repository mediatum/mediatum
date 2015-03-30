# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from json import dumps
from warnings import warn

import pyaml
from sqlalchemy import (Column, Table, ForeignKey, Sequence,
                        Integer, Unicode, Text, String, sql, text)
from sqlalchemy.orm import relationship, backref, deferred, Query
from sqlalchemy.orm.dynamic import AppenderQuery
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql.json import JSONElement

from core.node import NodeMixin
from utils.magicobjects import MInt
from . import DeclarativeBase
from core.database.postgres import db_metadata
from core.database.postgres.compilerext import view

C = Column
FK = ForeignKey
rel = relationship
bref = backref

logg = logging.getLogger(__name__)


class LenMixin(object):

    def __len__(self):
        warn("use query.count() instead", DeprecationWarning)
        return self.count()


class AppenderQueryWithLen(AppenderQuery, LenMixin):
    pass


class NodeAppenderQuery(AppenderQuery, LenMixin):

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


class Access(DeclarativeBase):

    """Used for ACL
    """
    __tablename__ = "access"
    name = C(String(64), primary_key=True)
    description = C(Text)
    rule = C(Text)


class Attributes(object):

    """
    Proxy for the attrs dict.
    Provides access to attribute values via dot notation.

    Examples:

    node.a.test == node.attrs["test"]
    """

    def __init__(self, obj):
        object.__setattr__(self, "obj", obj)

    def __getattr__(self, attr):
        return self.obj.attrs[attr]


class PythonicJSONElement(JSONElement):

    """
    Wraps a JSONElement for a more pythonic experience in SQLAlchemy expression with JSON attributes.
    Operators behave differently depending on the type of the right operand.
    Nested dict / list structures are supported.

    Examples:

        q(Document).filter(Document.a.title == "Some Title").one()
        q(Image).filter(Image.a.height >= 600)
        q(Document).filter(Document.a.title.between("a", "c")) # lexicographical order!

    => finds all documents with given title.
    """

    def __init__(self, left, right, *args, **kwargs):
        if hasattr(right, "__iter__"):
            self._path = list(right)
        else:
            self._path = [right]
        super(PythonicJSONElement, self).__init__(left, right, *args, **kwargs)

    def operate(self, op, *other, **kwargs):
        """This performs a JSON comparison (Postgres operator ->)."""
        if len(other) == 1:
            # this is just a optimization for special cases to avoid calling the JSON dump function; the final return is sufficient
            other = other[0]
            if isinstance(other, basestring):
                return super(JSONElement, self).operate(op, '"' + other + '"')
            elif isinstance(other, bool):
                return super(JSONElement, self).operate(op, str(other).lower())
            elif isinstance(other, (int, long)):
                return super(JSONElement, self).operate(op, str(other))
            return super(JSONElement, self).operate(op, dumps(other), **kwargs)
        # multiple operands given
        return super(JSONElement, self).operate(op, *(dumps(o) for o in other), **kwargs)

    # specialized text operators

    def like(self, other, **kwargs):
        return self.astext.like(other, **kwargs)

    def contains(self, other, **kwargs):
        return self.astext.contains(other, **kwargs)

    def startswith(self, other, **kwargs):
        return self.astext.startswith(other, **kwargs)

    def endswith(self, other, **kwargs):
        return self.astext.endswith(other, **kwargs)

    def match(self, other, **kwargs):
        return self.astext.match(other, **kwargs)

    @property
    def json(self):
        return JSONElement(self.left, self._path)

    def __getattr__(self, name):
        # XXX: could cause some exceptions when SQLAlchemy tries to check for attributes with getattr()
        if name.startswith("_") or name in ("is_literal", "key"):
            return object.__getattribute__(self, name)
        return PythonicJSONElement(self.left, self._path + [name])

    def __getitem__(self, item):
        if hasattr(item, "__iter__"):
            return PythonicJSONElement(self.left, self._path + list(item))
        else:
            return PythonicJSONElement(self.left, self._path + [item])


class AttributesExpressionAdapter(object):

    """
    Allows "natural" access to attributes in SQLAlchemy expressions, see `PythonicJSONElement`.

    """

    def __init__(self, obj):
        object.__setattr__(self, "obj", obj)

    def __getattr__(self, attr):
        return PythonicJSONElement(self.obj.attrs, attr)

    def __getitem__(self, item):
        if hasattr(item, "__iter__"):
            return PythonicJSONElement(self.obj.attrs, list(item))
        return PythonicJSONElement(self.obj.attrs, item)


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
        join(Node, Node.id == t_noderelation.c.cid).\
        cte(name="subtree")
    
    return query


def _cte_subtree_container(node):
    from contenttypes.container import Container
    from core import db

    query = db.query(t_noderelation.c.cid).\
        filter(t_noderelation.c.nid == node.id).\
        join(Container, Container.id == t_noderelation.c.cid).\
        cte(name="subtree")
    
    return query


class Node(DeclarativeBase, NodeMixin):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"

    _id = C(Integer, Sequence('node_id_seq', start=100), primary_key=True, name="id")
    type = C(Text, index=True)
    schema = C(Unicode, index=True)
    name = C(Unicode, index=True)
    orderpos = C(Integer, default=1, index=True)
    read_access = C(Text)
    write_access = C(Text)
    data_access = C(Text)
    fulltext = deferred(C(Text))
    localread = C(Text)

    attrs = deferred(C(MutableDict.as_mutable(JSONB)))

    @hybrid_property
    def id(self):
        if self._id:
            return MInt(self._id)

    @id.expression
    def id_expr(cls):
        return cls._id

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
            self._id = id
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
            filter(t_noderelation.c.distance == 1).distinct()
        
        return query

    def all_children_by_query(self, query):
        subtree = _cte_subtree(self)
        query = query.\
            join(subtree, Node.id == subtree.c.cid).\
            distinct()
        return query

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

### helpers for node child/parent relationships

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
    return relationship(*args, **extended_kwargs)


def all_children_rel(*args, **kwargs):
    extended_kwargs = _all_children_rel_options.copy()
    extended_kwargs.update(kwargs)
    return relationship(*args, **extended_kwargs)


def parents_rel(*args, **kwargs):
    extended_kwargs = _parents_rel_options.copy()
    extended_kwargs.update(kwargs)
    return relationship(*args, **extended_kwargs)

### define Node child/parent relationships here

Node.children = children_rel(Node, backref=bref("parents", lazy="dynamic", query_class=NodeAppenderQuery))
Node.all_children = all_children_rel(Node)
    


class BaseFile(DeclarativeBase):

    """Represents an item on the filesystem
    """
    __tablename__ = "nodefile"
    nid = C(Integer, FK(Node.id), primary_key=True, index=True)
    path = C(Unicode(4096), primary_key=True)
    filetype = C(Unicode(126), primary_key=True)
    mimetype = C(String(126))

    def __repr__(self):
        return "File for Node #{} ({}:{}|{}) at {}".format(
            self.nid, self.path, self.filetype, self.mimetype, hex(id(self)))
