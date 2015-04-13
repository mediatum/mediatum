# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from . import db_metadata, DeclarativeBase
import os.path


CONNECTSTR_TEMPLATE = "postgresql+psycopg2://{user}:{passwd}@{dbhost}:{dbport}/{database}"

logg = logging.getLogger(__name__)


def read_and_prepare_sql(sql_filepath):
    """Reads SQL code from a file, sets search path and strips comment + logging lines"""
    with open(os.path.join(os.path.dirname(__file__), "sql", sql_filepath)) as f:
        sql = f.read().replace(":search_path", "mediatum")
    sql_lines = sql.split("\n")
    return "\n".join(l for l in sql_lines if not l.startswith("--") and "RAISE" not in l)


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
        self.dbport = int(config.get("database.dbport", "5432"))
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

    def get_model_classes(self):
        from core.database.postgres.file import File
        from core.database.postgres.node import Node
        return (File, Node)

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
        from .node import Node
        return self.session.query(Node).get(node.id)

    def create_tables(self, conn):
        self.metadata.create_all(conn)

    def drop_tables(self, conn):
        self.metadata.drop_all(conn)

    def create_extra_indexes(self, conn):
        pass

    def drop_extra_indexes(self, conn):
        pass

    def create_functions(self, conn):
        conn.execute(read_and_prepare_sql("noderelation_funcs.sql"))
        conn.execute(read_and_prepare_sql("noderelation_rules_and_triggers.sql"))

    def drop_functions(self, conn):
        pass

    def create_all(self):
        with self.engine.begin() as conn:
            conn.execute("SET search_path TO " + self.metadata.schema)
            self.create_tables(conn)
            self.create_functions(conn)

    def drop_all(self):
        with self.engine.begin() as conn:
            conn.execute("SET search_path TO " + self.metadata.schema)
            self.drop_functions(conn)
            self.drop_tables(conn)
