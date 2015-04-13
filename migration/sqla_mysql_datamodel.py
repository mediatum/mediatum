# -*- coding: utf-8 -*-
'''
datamodel.py
Created on 06.06.2013
@author: stenzel
'''
from sqlalchemy import Column, ForeignKey, String, Text, Integer, Index, Table, Boolean, Unicode
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.hybrid import hybrid_property
from utils.compat import string_types
import codecs
C = Column
FK = ForeignKey
rel = relationship
bref = backref


def to_dict(self):
    return dict((col.name, getattr(self, col.name)) for col in self.__table__.columns)


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata
DeclarativeBase.to_dict = to_dict


class Access(DeclarativeBase):
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

t_access = Access.__table__


class Node(DeclarativeBase):
    __tablename__ = "node"
    id = C(Integer, primary_key=True)
    name = C(Unicode, index=True)
    type = C(Unicode, nullable=False, index=True)
    orderpos = C(Integer, default=1, index=True)
    readaccess = C(Text)
    writeaccess = C(Text)
    dataaccess = C(Text)
    dirty = C(Boolean)
    localread = C(Text)
    children = rel("Node",
                   backref="parents",
                   secondary=t_nodemapping,
                   lazy="dynamic",
                   primaryjoin=id == t_nodemapping.c.nid,
                   secondaryjoin=id == t_nodemapping.c.cid)
    attributes = rel("NodeAttribute",
                     backref=bref("node"),
                     collection_class=attribute_mapped_collection("name"),
                     cascade="save-update, delete, delete-orphan")

    def __init__(self, name, type, id=None, attributes=[]):
        self.name = name
        self.type = type
        if id is not None:
            self.id = id
        for attr in attributes:
            self.attributes.set(attr)

    def __unicode__(self):
        return u"Node #{} {}: {} at {}".format(self.id, self.name, self.type, hex(id(self)))

    def __repr__(self):
        return self.__unicode__().encode("utf8")

    def set(self, key, value):
        """Set an attribute"""
        attr = self.attributes.get(key)
        if not attr:
            attr = NodeAttribute(key, value)
        else:
            attr.value = value
        self.attributes.set(attr)

    def get(self, key):
        """Get an attribute value"""
        return self.attributes[key].value

    def delete(self, key):
        """Delete an attribute"""
        del self.attributes[key]

    __getitem__ = get
    __setitem__ = set
    __delitem__ = delete


t_node = Node.__table__


class NodeAttribute(DeclarativeBase):
    __tablename__ = "nodeattribute"
    nid = C(Integer, FK("node.id"), primary_key=True, index=True)
    name = C(Unicode, primary_key=True, index=True)
    _value = C(Unicode, name="value", nullable=True)

    @hybrid_property
    def value(self):
        if self._value is None:
            return None
        if self._value.startswith(b"\x11PACK\x12"):
            return msgpack.loads(self._value[6:], encoding="utf8")
        else:
            return unicode(self._value, encoding="utf8")

    @value.setter
    def set_value(self, newvalue):
        if isinstance(newvalue, string_types):
            self._value = codecs.encode(newvalue, "utf8")
        else:
            dval = msgpack.dumps(newvalue)
            val = b"\x11PACK\x12" + dval
            self._value = val

    def __init__(self, name=None, value=None, type=None, id=None):
        if name:
            self.name = name
        if value:
            self.value = value
        if type:
            self.type = type
        if id:
            self.id = id

    def __repr__(self):
        return u"Attribute for Node #{}: {}='{}' at {}".format(self.nid, self.name, self.value, hex(id(self))).encode("utf8")


Index(u'nid_2', NodeAttribute.__table__.c.nid, NodeAttribute.__table__.c.name)

t_nodeattribute = NodeAttribute.__table__


class NodeFile(DeclarativeBase):
    __tablename__ = "nodefile"
    nid = C(Integer, FK("node.id"), primary_key=True, index=True)
    filename = C(Unicode, primary_key=True)
    type = C(Unicode)
    node = rel("Node", backref=bref("files", cascade="delete"))
    mimetype = C(Unicode)

    def __repr__(self):
        return "File for Node #{} ({}) at {}".format(self.nid, self.filename, hex(id(self)))


t_nodefile = NodeFile.__table__
