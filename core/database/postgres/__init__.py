# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
import logging
import time

import pyaml
from ipaddr import IPv4Network, IPv4Address, AddressValueError
import psycopg2.extensions
from psycopg2.extensions import adapt, AsIs
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, event, Integer, DateTime, func as sqlfunc
from sqlalchemy.orm import relationship, backref, Query, Mapper, undefer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_continuum.utils import version_class
from sqlalchemy_continuum.plugins.transaction_meta import TransactionMetaPlugin
from sqlalchemy_continuum import versioning_manager
from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum.utils import parent_class

from core import config
from core.transition import request
from core.database.postgres.continuumext import MtVersionBase
from utils.compat import iteritems


logg = logging.getLogger(__name__)


C = Column
FK = ForeignKey
rel = relationship
bref = backref

DB_SCHEMA_NAME = "mediatum"


def dynamic_rel(*args, **kwargs):
    return relationship(*args, lazy="dynamic", **kwargs)


db_metadata = sqla.MetaData(schema=DB_SCHEMA_NAME)
mediatumfunc = getattr(sqlfunc, DB_SCHEMA_NAME)
DeclarativeBase = declarative_base(metadata=db_metadata)


class TimeStamp(object):

    """a simple timestamp mixin"""

    @declared_attr
    def created_at(cls):
        return C(DateTime, default=sqlfunc.now())


def integer_pk(**kwargs):
    return C(Integer, primary_key=True, **kwargs)


def integer_fk(*args, **kwargs):
    if len(args) == 2:
        return C(args[0], ForeignKey(args[1]), **kwargs)
    elif len(args) == 1:
        return C(ForeignKey(args[0]), **kwargs)
    else:
        raise ValueError("at least one argument must be specified (type)!")


# some pretty printing for SQLAlchemy objects ;)


def to_dict(self):
    return dict((str(col.name), getattr(self, col.name))
                for col in self.__table__.columns)


def to_yaml(self):
    return pyaml.dump(self.to_dict())


def update(self, **kwargs):
    for name, value in iteritems(kwargs):
        setattr(self, name, value)

def __str__(self):
    if hasattr(self, "__unicode__"):
        return unicode(self).encode("utf8")
    return repr(self)


DeclarativeBase.to_dict = to_dict
DeclarativeBase.to_yaml = to_yaml
DeclarativeBase.update = update
DeclarativeBase.__str__ = __str__


# IP types handling

def adapt_ipv4network(ipnet):
    val = adapt(str(ipnet)).getquoted()
    return AsIs(val + "::cidr")


def adapt_ipv4address(ipnet):
    val = adapt(str(ipnet)).getquoted()
    return AsIs(val + "::inet")

psycopg2.extensions.register_adapter(IPv4Network, adapt_ipv4network)
psycopg2.extensions.register_adapter(IPv4Address, adapt_ipv4address)
psycopg2.extensions.register_type(psycopg2.extensions.new_array_type((651,), "CIDR[]", psycopg2.STRING))


# Date types handling

class InfDateAdapter(object):

    """Map datetime.date.min/max values to infinity in Postgres
    Taken from: http://initd.org/psycopg/docs/usage.html"""

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def getquoted(self):
        if self.wrapped == datetime.date.max:
            return b"'infinity'::date"
        elif self.wrapped == datetime.date.min:
            return b"'-infinity'::date"
        else:
            return psycopg2.extensions.DateFromPy(self.wrapped).getquoted()

psycopg2.extensions.register_adapter(datetime.date, InfDateAdapter)


def build_accessfunc_arguments(user=None, ip=None, date=None, req=None):
    """Build the expected arguments for the DB permission procedures has_*_access_to_node()
    IP and date are returned unchanged when passed to this function. 
    For missing arguments, default values are set from request information or current date.
    :returns: 3-tuple of group_ids, ip and date
        For admin users, it returns (None, None, None) which means: ignore all access checks.
        Users can test for this and skip permission checks completely.
    """
    from core.users import get_guest_user

    if user is None and ip is None:
        if req is None:
            req = request

        from core.users import user_from_session

        user = user_from_session(req.session)
        # XXX: like in mysql version, what's the real solution?
        try:
            ip = IPv4Address(req.remote_addr)
        except AddressValueError:
            logg.warn("illegal IP address %s, refusing IP-based access", req.remote_addr)
            ip = None

    if user is None:
        user = get_guest_user()

    # admin sees everything ;)
    if user.is_admin:
        return (None, None, None)

    if ip is None:
        ip = IPv4Address("0.0.0.0")
    
    if date is None:
        date = sqlfunc.current_date()

    return user.group_ids, ip, date
        

class MtQuery(Query):

    def prefetch_attrs(self):
        from core import Node
        return self.options(undefer(Node.attrs))

    def prefetch_system_attrs(self):
        from core import Node
        return self.options(undefer(Node.system_attrs))

    def _find_nodeclass(self):
        from core import Node
        """Returns the query's underlying model classes."""
        return [
            d['entity']
            for d in self.column_descriptions
            if issubclass(d['entity'], Node)
        ]

    def filter_read_access(self, user=None, ip=None, req=None):
        return self._filter_access("read", user, ip, req)

    def filter_write_access(self, user=None, ip=None, req=None):
        return self._filter_access("write", user, ip, req)

    def filter_data_access(self, user=None, ip=None, req=None):
        return self._filter_access("data", user, ip, req)

    def _filter_access(self, accesstype, user=None, ip=None, req=None):
        group_ids, ip, date = build_accessfunc_arguments(user, ip, req)
        
        if group_ids is None and ip is None and date is None:
            # everything is None means: permission checks always pass, so we can skip access checks completely.
            # This will happen for an admin user.
            return self
        
        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return self
        else:
            nodeclass = nodeclass[0]

        db_funcs = {
            "read": mediatumfunc.has_read_access_to_node,
            "write": mediatumfunc.has_write_access_to_node,
            "data": mediatumfunc.has_data_access_to_node
        }

        try:
            db_accessfunc = db_funcs[accesstype]
        except KeyError:
            raise ValueError("accesstype '{}' does not exist, accesstype must be one of: read, write, data".format(accesstype))

        access_filter = db_accessfunc(nodeclass.id, group_ids, ip, date)
        return self.filter(access_filter)

    def get(self, ident):
        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return Query.get(self, ident)
        else:
            nodeclass = nodeclass[0]
        active_version = Query.get(self, ident)
        Transaction = versioning_manager.transaction_cls
        if active_version is None:
            ver_cls = version_class(nodeclass)
            return (self.session.query(ver_cls).join(Transaction, ver_cls.transaction_id == Transaction.id)
                    .join(Transaction.meta_relation)
                    .filter_by(key=u'alias_id', value=unicode(ident)).scalar())

        return active_version
    