# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import time
import pyaml
import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy import Column, ForeignKey, event, Integer, DateTime, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr


logg = logging.getLogger(__name__)


C = Column
FK = ForeignKey
rel = relationship
bref = backref


def dynamic_rel(*args, **kwargs):
        return relationship(*args, lazy="dynamic", **kwargs)


class TimeStamp(object):

    """a simple timestamp mixin"""

    @declared_attr
    def created_at(cls):
        return C(DateTime, default=func.now())


def integer_pk(**kwargs):
    return C(Integer, primary_key=True, **kwargs)


def integer_fk(*args, **kwargs):
    if len(args) == 2:
        return C(args[0], ForeignKey(args[1]), **kwargs)
    elif len(args) == 1:
        return C(ForeignKey(args[0]), **kwargs)
    else:
        raise ValueError("at least one argument must be specified (type)!")


db_metadata = sqla.MetaData(schema="mediatum")
DeclarativeBase = declarative_base(metadata=db_metadata)

# some pretty printing for SQLAlchemy objects ;)


def to_dict(self):
    return dict((str(col.name), getattr(self, col.name))
                for col in self.__table__.columns)


def to_yaml(self):
    return pyaml.dump(self.to_dict())


DeclarativeBase.to_dict = to_dict
DeclarativeBase.to_yaml = to_yaml


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement,
                          parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    conn.info.setdefault('current_query', []).append(statement)


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement,
                         parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    # total in seconds
    if total > 0.1:
        statement = conn.info['current_query'].pop(-1)
        logg.warn("slow query %.1fms:\n%s", total * 1000, statement)
