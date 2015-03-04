# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from warnings import warn

from sqlalchemy import (create_engine, Column, Table, ForeignKey, Index, Sequence,
                        Integer, Unicode, Text, String)
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session, deferred
from sqlalchemy.orm.dynamic import AppenderQuery
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta

from core import config
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property
import pyaml
from utils.magicobjects import MInt
from core.node import NodeMixin

from . import DeclarativeBase
from core.database.postgres import db_metadata

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


# definitions
t_nodemapping = Table("nodemapping", db_metadata,
                      C("nid", Integer, FK("node.id"), primary_key=True, index=True),
                      C("cid", Integer, FK("node.id", ondelete="CASCADE"), primary_key=True, index=True))


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
    Provides access to attribute values via dot notation and works as SQLAlchemy expression.

    Examples:

    object level (XXX: do we want this?):

        node.a.test == node.attrs["test"]

    class level:

        q(Document).filter(Document.a.title == "Some Title")

    => finds all documents with given title.
    """

    def __init__(self, obj):
        object.__setattr__(self, "obj", obj)

    def __getattr__(self, attr):
        return self.obj.attrs[attr]

    def __setattr__(self, attr, value):
        self.obj.attrs[attr] = value


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


child_rel_options = dict(
    secondary=t_nodemapping,
    lazy="dynamic",
    primaryjoin="Node.id == nodemapping.c.nid",
    secondaryjoin="Node.id == nodemapping.c.cid",
    query_class=NodeAppenderQuery
)

parent_rel_options = dict(
    secondary=t_nodemapping,
    lazy="dynamic",
    primaryjoin="Node.id == nodemapping.c.cid",
    secondaryjoin="Node.id == nodemapping.c.nid",
    query_class=NodeAppenderQuery
)


def _cte_subtree(node):
    from core import db
    t = db.query(t_nodemapping.c.cid).\
        filter(t_nodemapping.c.nid == node.id).\
        cte(name="subtree", recursive=True)

    return t.union_all(
        db.query(t_nodemapping.c.cid).
        join(Node, Node.id == t_nodemapping.c.cid).
        filter(t_nodemapping.c.nid == t.c.cid)
    )
    
    
def _cte_subtree_container(node):
    from contenttypes.container import Container
    from core import db
    t = db.query(t_nodemapping.c.cid).\
        filter(t_nodemapping.c.nid == node.id).\
        cte(name="subtree", recursive=True)

    return t.union_all(
        db.query(t_nodemapping.c.cid).
        join(Container, Container.id == t_nodemapping.c.cid).
        filter(t_nodemapping.c.nid == t.c.cid)
    )


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
    children = rel("Node", backref=bref("parents", lazy="dynamic", query_class=NodeAppenderQuery), **child_rel_options)
    content_children = rel("Content", **child_rel_options)

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
            join(t_nodemapping, Node.id == t_nodemapping.c.cid).\
            join(subtree, subtree.c.cid == t_nodemapping.c.nid)

        return query

    def all_children_by_query(self, query):
        subtree = _cte_subtree(self)
        query = query.\
            join(subtree, Node.id == subtree.c.cid)
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
