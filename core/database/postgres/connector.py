# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from warnings import warn

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from . import db_metadata, DeclarativeBase


CONNECTSTR_TEMPLATE = "postgresql+psycopg2://{user}:{passwd}@{dbhost}:{dbport}/{database}"

logg = logging.getLogger(__name__)


class PostgresSQLAConnector(object):

    """Basic db object used by the application
    """

    def __init__(self):
        session_factory = sessionmaker()
        self.Session = scoped_session(session_factory)
        self.metadata = db_metadata

    def connect(self):
        from core import config
        self.dbhost = config.get("database.dbhost", "localhost")
        self.dbport = int(config.get("database.dbport", "5342"))
        self.database = config.get("database.db", "mediatum")
        self.user = config.get("database.user", "mediatumadmin")
        self.passwd = config.get("database.passwd", "")
        self.connectstr = CONNECTSTR_TEMPLATE.format(**self.__dict__)
        logg.info("Connecting to %s", self.connectstr)
        engine = create_engine(self.connectstr)
        DeclarativeBase.metadata.bind = engine
        self.conn = engine.connect()
        self.engine = engine
        self.Session.configure(bind=engine)

    def make_session(self):
        """Create a session. 
        For testing purposes (used in core.test.factories, for example).
        """
        return self.Session()
    
    @property
    def session(self):
        return self.Session()

    def query(self, *entities, **kwargs):
        """Query proxy.
        :see: sqlalchemy.orm.session.Session.query
        
        Example:
        
        from core import db
        q = db.query
        q(Node).get(42)
        """
        return self.Session().query(*entities, **kwargs)
    
    
    def refresh(self, node):
        """Return a refreshed copy of `node`.
        Workaround for Node objects which are kept between requests.
        XXX: must be removed later
        """
        from .model import Node
        return self.session.query(Node).get(node.id)

