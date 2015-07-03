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
from core.database.postgres import MtQuery
from core.database.postgres.psycopg2_debug import make_debug_connection_factory

# set this to True or False to override debug config settings
DEBUG = None
DEBUG_SHOW_TRACE = None

CONNECTSTR_TEMPLATE = "postgresql+psycopg2://{user}:{passwd}@{dbhost}:{dbport}/{database}"
CONNECTSTR_TEMPLATE_WITHOUT_PW = "postgresql+psycopg2://{user}:<passwd>@{dbhost}:{dbport}/{database}"

logg = logging.getLogger(__name__)


def read_and_prepare_sql(sql_filepath, sql_dir=None, filter_notices=True, filter_comments=True):
    """Reads SQL code from a file, sets search path and strips comment + logging lines"""
    if sql_dir is None:
        sql_dir = os.path.join(os.path.dirname(__file__), "sql")

    with open(os.path.join(sql_dir, sql_filepath)) as f:
        sql = f.read().replace(":search_path", "mediatum").replace("%", "%%")

    if filter_notices or filter_comments:
        sql_lines = sql.split("\n")
        return "\n".join(l for l in sql_lines
                         if (not filter_comments or not l.startswith("--"))
                         and (not filter_notices or "RAISE NOTICE" not in l))
    else:
        return sql


class PostgresSQLAConnector(object):

    """Basic db object used by the application
    """

    def __init__(self):
        session_factory = sessionmaker(query_cls=MtQuery)
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

        if DEBUG is None:
            self.debug = config.get("database.debug", "").lower() == "true"
        else:
            self.debug = DEBUG
            
        if self.debug:
            if DEBUG_SHOW_TRACE is None:
                show_trace = config.get("database.debug_show_trace", "").lower() == "true"
            else:
                show_trace = DEBUG_SHOW_TRACE
            connect_args = {"connection_factory": make_debug_connection_factory(show_trace)}
        else:
            connect_args = {}

        logg.info("Connecting to %s", CONNECTSTR_TEMPLATE_WITHOUT_PW.format(**self.__dict__))
        engine = create_engine(self.connectstr, connect_args=connect_args)

        DeclarativeBase.metadata.bind = engine
        self.engine = engine
        self.Session.configure(bind=engine)

    def get_model_classes(self):
        from core.database.postgres.file import File
        from core.database.postgres.node import Node
        from core.database.postgres.user import User, UserGroup, AuthenticatorInfo
        from core.database.postgres.shoppingbag import ShoppingBag
        from core.database.postgres.permission import AccessRule, AccessRuleset, NodeToAccessRule, NodeToAccessRuleset
        return (
            File,
            Node,
            User,
            UserGroup,
            AuthenticatorInfo,
            ShoppingBag,
            AccessRule,
            AccessRuleset,
            NodeToAccessRule,
            NodeToAccessRuleset)

    def make_session(self):
        """Create a session.
        For testing purposes (used in core.test.factories, for example).
        """
        return self.Session()

    @property
    def session(self):
        return self.Session()

    @property
    def statement_history(self):
        if not self.debug:
            raise Exception("connector debugging disabled (cfg: database.debug), statement history not available")
        return self.Session().connection().connection.connection.history

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
        # Fts is imported nowhere else, make it known to SQLAlchemy by importing it here
        from core.database.postgres.search import Fts
        self.metadata.create_all(conn)

    def drop_tables(self, conn):
        self.metadata.drop_all(conn)

    def create_extra_indexes(self, conn):
        pass

    def drop_extra_indexes(self, conn):
        pass

    def create_functions(self, conn):
        conn.execute(read_and_prepare_sql("mediatum_utils.sql"))
        conn.execute(read_and_prepare_sql("noderelation_funcs.sql"))
        conn.execute(read_and_prepare_sql("json.sql"))
        conn.execute(read_and_prepare_sql("nodesearch.sql"))
        conn.execute(read_and_prepare_sql("node_access_funcs.sql"))
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
