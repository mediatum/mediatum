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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta

from core import config
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property

C = Column
FK = ForeignKey
rel = relationship
bref = backref


def to_dict(self):
    return dict((col.name, getattr(self, col.name))
                for col in self.__table__.columns)


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata
DeclarativeBase.to_dict = to_dict


logg = logging.getLogger("database")

CONNECTSTR_TEMPLATE = "postgresql+psycopg2://{user}:{passwd}@{dbhost}:{dbport}/{database}"


class LenMixin(object):

    def __len__(self):
        warn("use query.count() instead", DeprecationWarning)
        return self.count()


class NodeAppenderQuery(AppenderQuery, LenMixin):

    """Custom AppenderQuery class with additional methods for node handling
    """

    def sort_by_orderpos(self, reverse=False):
        if reverse:
            warn("use .order_by(Node.orderpos.desc()) instead", DeprecationWarning)
            return self.order_by(BaseNode.orderpos.desc())
        else:
            warn("use .order_by(Node.orderpos) instead", DeprecationWarning)
            return self.order_by(BaseNode.orderpos)

    def sort_by_name(self, direction="up"):
        reverse = direction != "up"
        if reverse:
            warn("use .order_by(Node.name.desc()) instead", DeprecationWarning)
            return self.order_by(BaseNode.name.desc())
        else:
            warn("use .order_by(Node.name) instead", DeprecationWarning)
            return self.order_by(BaseNode.name)

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
                expr = BaseNode.attrs[field[1:]].astext.desc()
            else:
                expr = BaseNode.attrs[field].astext
            query = query.order_by(expr)

        return query


# definitions


class Access(DeclarativeBase):

    """Used for ACL
    """
    __tablename__ = "access"
    name = C(String(64), primary_key=True)
    description = C(Text)
    rule = C(Text)

t_nodemapping = Table("nodemapping", metadata,
                      C("nid", Integer, FK("node.id"), primary_key=True),
                      C("cid", Integer, FK("node.id", ondelete="CASCADE"), primary_key=True))


Index(u'cid', t_nodemapping.c.cid)
Index(u'cid_2', t_nodemapping.c.cid, t_nodemapping.c.nid)
Index(u'nid', t_nodemapping.c.nid)
Index(u'nid_2', t_nodemapping.c.nid, t_nodemapping.c.cid)


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


class MInt(int):

    """'Magic' class which represents an integer value but converts itself to a string if needed.
    We need this because legacy code treats node ids as string and concatenates ids to strings.
    This is a stupid idea, so it raises a DeprecationWarning if it's used as a string ;)
    """

    def __new__(cls, value):
        return super(MInt, cls).__new__(cls, value)

    def __add__(self, other):
        if isinstance(other, str):
            warn("magic cast int --> str in addition (left op)", DeprecationWarning)
            return str(self) + other
        return super(MInt, self).__add__(other)

    def __radd__(self, other):
        if isinstance(other, str):
            warn("magic cast int --> str in addition (right op)", DeprecationWarning)
            return other + str(self)
        return super(MInt, self).__add__(other)


class BaseNode(DeclarativeBase):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"

    _id = C(Integer, Sequence('node_id_seq', start=100), primary_key=True, name="id")
    type = C(Text)
    schema = C(Unicode)
    name = C(Unicode)
    orderpos = C(Integer, default=1, index=True)
    read_access = C(Text)
    write_access = C(Text)
    data_access = C(Text)
    fulltext = deferred(C(Text))
    localread = C(Text)
    children = rel("Node", backref=bref("parents", lazy="dynamic", query_class=NodeAppenderQuery), **child_rel_options)
    content_children = rel("ContentType", **child_rel_options)

    attrs = deferred(C(MutableDict.as_mutable(JSONB)))

    @hybrid_property
    def id(self):
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

    __mapper_args__ = {
        'polymorphic_identity': 'basenode',
        'polymorphic_on': type
    }


Index(u'node_name', BaseNode.__table__.c.name)
Index(u'node_type', BaseNode.__table__.c.type)
Index(u'node_orderpos', BaseNode.__table__.c.orderpos)


class BaseFile(DeclarativeBase):

    """Represents an item on the filesystem
    """
    __tablename__ = "nodefile"
    nid = C(Integer, FK(BaseNode.id), primary_key=True, index=True)
    path = C(Unicode(4096), primary_key=True)
    filetype = C(Unicode(126), primary_key=True)
    mimetype = C(String(126))

    def __repr__(self):
        return "File for Node #{} ({}:{}|{}) at {}".format(
            self.nid, self.path, self.filetype, self.mimetype, hex(id(self)))


Index(u'nodefile_nid', BaseFile.__table__.c.nid)


class PostgresSQLAConnector(object):

    """Basic db object used by the application
    """

    def __init__(self):
        self.dbhost = config.get("database.dbhost", "localhost")
        self.dbport = int(config.get("database.dbport", "5342"))
        self.database = config.get("database.db", "mediatum")
        self.user = config.get("database.user", "mediatumadmin")
        self.passwd = config.get("database.passwd", "")
        connectstr = CONNECTSTR_TEMPLATE.format(**self.__dict__)
        logg.info("Connecting to %s", connectstr)

        engine = create_engine(connectstr)
        DeclarativeBase.metadata.bind = engine
        session_factory = sessionmaker(bind=engine)
        self.Session = scoped_session(session_factory)
        self.conn = engine.connect()
        self.engine = engine
        self.metadata = metadata

    @property
    def session(self):
        return self.Session()

    @property
    def query(self):
        return self.Session().query
