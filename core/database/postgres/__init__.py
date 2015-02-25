# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import time
import pyaml
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy import event


logg = logging.getLogger(__name__)


DeclarativeBase = declarative_base()
db_metadata = DeclarativeBase.metadata

# some pretty printing for SQLAlchemy objects ;)


def to_dict(self):
    return dict((str(col.name), getattr(self, col.name))
                for col in self.__table__.columns)


def to_yaml(self):
    return pyaml.dump(self.to_dict())


DeclarativeBase.to_dict = to_dict
DeclarativeBase.to_yaml = to_yaml
