# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging

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

    def get_node_class(self):
        from .model import Node
        return Node

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

    @classmethod
    def _get_managed_tables(cls):
        """Returns all tables which should be managed by SQLAlchemy"""
        from .model import Access, Node, BaseFile, t_nodemapping
        return [Access.__table__, Node.__table__, BaseFile.__table__, t_nodemapping] 

    def create_tables(self, conn):
        self.metadata.create_all(conn, tables=PostgresSQLAConnector._get_managed_tables())
        
    def drop_tables(self, conn):
        self.metadata.drop_all(conn, tables=PostgresSQLAConnector._get_managed_tables())
        
    def create_views(self, conn):
        pass
        
    def drop_views(self, conn):
        pass
        
    def drop_extra_indexes(self, conn):
        pass

    def create_functions(self, conn):
        pass

    def drop_functions(self, conn):
        pass

    def create_all(self):
        with self.engine.begin() as conn:
            self.create_tables(conn)
            self.create_views(conn)
            self.create_functions(conn)

    def drop_all(self):
        with self.engine.begin() as conn:
            self.drop_functions(conn)
            self.drop_views(conn)
            self.drop_tables(conn)
            