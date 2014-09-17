# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
import logging

from sqlalchemy import (create_engine, Column, Table, ForeignKey, Index, Sequence,
                        Integer, Unicode, Text, String)
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session, deferred
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgres import JSONB
from core import config
from sqlalchemy.ext.declarative.api import DeclarativeMeta

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
                      C("cid", Integer, FK("node.id"), primary_key=True))


Index(u'cid', t_nodemapping.c.cid)
Index(u'cid_2', t_nodemapping.c.cid, t_nodemapping.c.nid)
Index(u'nid', t_nodemapping.c.nid)
Index(u'nid_2', t_nodemapping.c.nid, t_nodemapping.c.cid)


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


class BaseNode(DeclarativeBase):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"

    id = C(Integer, Sequence('node_id_seq', start=100), primary_key=True)
    type = C(Text)
    schema = C(Unicode)
    name = C(Unicode)
    orderpos = C(Integer, default=1, index=True)
    read_access = C(Text)
    write_access = C(Text)
    data_access = C(Text)
    fulltext = deferred(C(Text))
    localread = C(Text)

    child_kwargs = dict(
        secondary=t_nodemapping,
        lazy="dynamic",
        primaryjoin=id == t_nodemapping.c.nid,
        secondaryjoin=id == t_nodemapping.c.cid)

    children = rel("BaseNode", backref="parents", **child_kwargs)
    container_children = rel("ContainerType", **child_kwargs)
    content_children = rel("ContentType", **child_kwargs)

    attrs = C(JSONB)


Index(u'node_name', BaseNode.__table__.c.name)
Index(u'node_type', BaseNode.__table__.c.type)
Index(u'node_orderpos', BaseNode.__table__.c.orderpos)


class NodeFile(DeclarativeBase):

    """Represents an item on the filesystem
    """
    __tablename__ = "nodefile"
    nid = C(Integer, FK("node.id"), primary_key=True, index=True)
    filename = C(Unicode(255), primary_key=True)
    type = C(Unicode(50), primary_key=True)
    node = rel("BaseNode", backref=bref("files", cascade="delete"))
    mimetype = C(String(20))

    def __repr__(self):
        return "File for BaseNode #{} ({}) at {}".format(
            self.nid, self.filename, hex(id(self)))


Index(u'nodefile_nid', NodeFile.__table__.c.nid)


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

    @property
    def query(self):
        return self.Session().query
