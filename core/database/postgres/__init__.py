# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import datetime
import logging

import ruamel.yaml as _ruamel_yaml
from ipaddr import IPv4Network, IPv4Address, AddressValueError
import psycopg2.extensions
from psycopg2.extensions import adapt, AsIs
import sqlalchemy as _sqlalchemy
import sqlalchemy.orm as _
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, DateTime, func as sqlfunc
from sqlalchemy.ext.declarative import declared_attr

import flask as _flask
from core.database.postgres.continuumext import MtVersionBase
from utils.compat import iteritems

import core as _core

logg = logging.getLogger(__name__)


C = Column
FK = ForeignKey
rel = _sqlalchemy.orm.relationship
bref = _sqlalchemy.orm.backref

DB_SCHEMA_NAME = "mediatum"


def dynamic_rel(*args, **kwargs):
    return _sqlalchemy.orm.relationship(*args, lazy="dynamic", **kwargs)


db_metadata = _sqlalchemy.MetaData(schema=DB_SCHEMA_NAME)
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
    return _ruamel_yaml.round_trip_dump(self.to_dict())


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
    if user is None and ip is None:
        if req is None:
            req = _flask.request

        user = _core.users.user_from_session()
        # XXX: like in mysql version, what's the real solution?
        try:
            ip = IPv4Address(req.remote_addr)
        except AddressValueError:
            logg.warning("illegal IP address %s, refusing IP-based access", req.remote_addr)
            ip = None

    if user is None:
        user = _core.users.get_guest_user()

    # admin sees everything ;)
    if user.is_admin:
        return (None, None, None)

    if ip is None:
        ip = IPv4Address("0.0.0.0")
    
    if date is None:
        date = sqlfunc.current_date()

    return user.group_ids, ip, date
