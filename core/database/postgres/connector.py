# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import atexit
import pwd
import os.path
from subprocess import check_call, check_output, call

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy_continuum.utils import version_class

from core import config
from . import db_metadata, DeclarativeBase
from core.database.postgres import MtQuery
from core.database.postgres.psycopg2_debug import make_debug_connection_factory
from core.database.init import init_database_values
from utils.utils import find_free_port
from utils.postgres import schema_exists, table_exists

# set this to True or False to override debug config settings
DEBUG = None
DEBUG_SHOW_TRACE = None

CONNECTSTR_TEMPLATE = "postgresql+psycopg2://{user}:{passwd}@{host}:{port}/{database}"
CONNECTSTR_TEMPLATE_TEST_DB = "postgresql+psycopg2://{user}@:{port}/{database}?host={socketdir}"
CONNECTSTR_TEMPLATE_WITHOUT_PW = "postgresql+psycopg2://{user}:<passwd>@{host}:{port}/{database}"

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


def disabled_scoped_session(*args, **kwargs):
    raise Exception("Test mode, database session disabled. Use the core.test.fixtures.session fixture!")


class ConnectionException(Exception):
    pass


class PostgresSQLAConnector(object):

    """Basic db object used by the application
    """

    def __init__(self):
        session_factory = sessionmaker(query_cls=MtQuery)
        self.Session = scoped_session(session_factory)
        self.metadata = db_metadata

    def configure(self, force_test_db=False):
        if DEBUG is None:
            self.debug = config.get("database.debug", "").lower() == "true"
        else:
            self.debug = DEBUG

        if force_test_db:
            logg.warn("WARNING: force_test_db requested, creating / using test database server", trace=False)
            test_db = True
        else:
            test_db = config.get("database.test_db", "false").lower() == "true"
            if test_db:
                logg.warn("WARNING: database.test_db enabled in config, creating / using test database server", trace=False)

        self.test_db = test_db

        if not test_db:
            self.host = config.get("database.host", "localhost")
            self.port = int(config.get("database.port", "5432"))
            self.database = config.get("database.db", "mediatum")
            self.user = config.get("database.user", "mediatum")
            self.passwd = config.get("database.passwd", "mediatum")
            self.connectstr = CONNECTSTR_TEMPLATE.format(**self.__dict__)
            logg.info("using database connection string: %s", CONNECTSTR_TEMPLATE_WITHOUT_PW.format(**self.__dict__))
        # test_db is handled in create_engine / check_run_test_db_server

    def check_create_test_db(self):
        # check database existence
        out = self.run_psql_command("SELECT 1 FROM pg_database WHERE datname='mediatum'", output=True, database="postgres")
        if out.strip() != "1":
            # no mediaTUM database present, use postgres as starting point to create one
            self.run_psql_command("CREATE DATABASE mediatum OWNER=" + self.user, database="postgres")
            self.run_psql_command("CREATE EXTENSION hstore SCHEMA public")
            self.run_psql_command("ALTER ROLE {} SET search_path TO mediatum,public".format(self.user))

    def check_run_test_db_server(self):
        dirpath = config.check_create_test_db_dir()
        # database role name must be the same as the process user
        user = pwd.getpwuid(os.getuid())[0]
        code = call(["pg_ctl", "status", "-D", dirpath])
        if code:
            # error code > 0? database dir is not present or server not running
            if code == 4:
                # dirpath is not a proper database directory, try to init it
                check_call(["pg_ctl", "init", "-D", dirpath])
            elif code == 3:
                # database directory is ok, but no server running
                logg.info("using existing database directory %s", dirpath)
            else:
                # should not happen with the tested postgres version...
                raise ConnectionException("unexpected exit code from pg_ctl: %s. This looks like a bug.".format(code))

            port = find_free_port()
            socketdir = "/tmp"
            logg.info("starting temporary postgresql server on port %s as user %s", port, user)
            check_call(["pg_ctl", "start", "-w", "-D", dirpath, "-o", "'-p {}'".format(port)])

            # we have started the database server, it should be stopped automatically if mediaTUM exits
            def stop_db():
                self.Session.close_all()
                self.engine.dispose()
                check_call(["pg_ctl", "stop", "-D", dirpath])

            atexit.register(stop_db)
        else:
            # server is already running, get information from database dir
            with open(os.path.join(dirpath, "postmaster.pid")) as f:
                lines = f.readlines()
                port = int(lines[3])
                socketdir = lines[4]

        # finally set the database config params for engine creation
        self.port = port
        self.host = "localhost"
        self.passwd = ""
        self.user = user
        self.database = "mediatum"
        self.socketdir = socketdir
        self.connectstr = CONNECTSTR_TEMPLATE_TEST_DB.format(**self.__dict__)
        logg.info("using test database connection string: %s", self.connectstr)

    def create_engine(self):
        if self.debug:
            if DEBUG_SHOW_TRACE is None:
                show_trace = config.get("database.debug_show_trace", "").lower() == "true"
            else:
                show_trace = DEBUG_SHOW_TRACE
            connect_args = {"connection_factory": make_debug_connection_factory(show_trace)}
        else:
            connect_args = {}

        if self.test_db:
            self.check_run_test_db_server()
            self.check_create_test_db()

        engine = create_engine(self.connectstr, connect_args=connect_args)
        db_connection_exception = self.check_db_connection(engine)

        if db_connection_exception:
            if self.test_db:
                msg = "Could not connect to temporary test database, error was: " + db_connection_exception.args[0]
                msg += "This looks like a bug in mediaTUM or a strange problem with your system."
            else:
                msg = "Could not connect to database, error was: " + db_connection_exception.args[0]
                if config.is_default_config():
                    msg += "HINT: You are running mediaTUM without a config file. Did you forget to create one?" \
                           "\nTo start mediaTUM without a config file using a temporary test database server, use" \
                           " the --force-test-db option on the command line." \
                           "\nSee --help for more info."
                else:
                    msg += "check the settings in the [database] section in your config file."

            raise ConnectionException(msg)

        DeclarativeBase.metadata.bind = engine
        self.engine = engine
        self.Session.configure(bind=engine)

        if self.test_db:
            # create schema with default data in test_db mode if not present
            self.check_create_schema(set_alembic_version=False)
            self.check_load_initial_database_values(default_admin_password=u"insecure")

    def check_db_connection(self, engine):
        try:
            conn = engine.connect()
        except Exception as e:
            return e

        res = conn.execute("select version()")
        version = res.fetchone()
        logg.info("db connection test succeeded, version is: %s", version[0])
        conn.close()

    def check_db_structure_validity(self):
        """Just a simple check if the schema and the node table exist, should be extended"""
        if not schema_exists(self.session, "mediatum"):
            # missing schema, user should run schema creation or import a dump with structure
            raise Exception("'mediatum' database schema does not exist."
                            "HINT: Did you forget to run 'bin/manage.py schema create'?")

        if not table_exists(self.session, "mediatum", "node"):
            # missing node table, there's something really wrong here...
            raise Exception("'node' table does not exist."
                            "HINT: You can delete and recreate the database schema with all tables with 'bin/manage.py schema recreate'")

    def get_model_classes(self):
        from core.database.postgres.file import File
        from core.database.postgres.node import NodeType, Node, NodeAlias
        from core.database.postgres.user import User, UserGroup, AuthenticatorInfo
        from core.database.postgres.shoppingbag import ShoppingBag
        from core.database.postgres.permission import AccessRule, AccessRuleset, NodeToAccessRule, NodeToAccessRuleset
        from core.database.postgres.setting import Setting
        from core.database.postgres.search import Fts
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
            NodeToAccessRuleset,
            Setting,
            Fts,
            NodeType,
            NodeAlias)

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
        NodeVersion = version_class(Node)
        if isinstance(node, NodeVersion):
            return self.session.query(NodeVersion).get((node.id, node.transaction.id))
        else:
            return self.session.query(Node).get(node.id)

    # database manipulation helpers

    def drop_schema(self):
        s = self.session
        s.execute("DROP SCHEMA mediatum CASCADE")
        s.commit()
        logg.info("dropped database structure")

    def create_schema(self, set_alembic_version=True):
        """Creates the 'mediatum' schema.
        :param set_alembic_version: Stamp database with current alembic revision information. Defaults to True.
        Can be disabled if a schema for testing is going to be created.
        """
        s = self.session
        logg.info("creating DB schema...")
        s.execute("CREATE SCHEMA mediatum")
        s.commit()
        try:
            self.create_all()
            if set_alembic_version:
                # create alembic version table and set current alembic version to head
                from alembic.config import Config
                from alembic import command
                alembic_cfg = Config(os.path.join(config.basedir, "alembic.ini"))
                alembic_cfg.attributes["running_in_mediatum"] = True
                command.stamp(alembic_cfg, "head")
            s.commit()
            logg.info("commited database structure")
        except:
            # I tried to use a transaction to enclose everything, but sqlalchemy (?) fails when the schema is created within the transaction
            # solution: just drop the schema it if something fails after schema creation
            s.execute("DROP SCHEMA mediatum CASCADE")
            raise

    def check_create_schema(self, set_alembic_version=True):
        if not schema_exists(self.session, "mediatum"):
            self.create_schema()

    def upgrade_schema(self):
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(config.basedir, "alembic.ini"))
        command.upgrade(alembic_cfg, "head")

    def check_load_initial_database_values(self, default_admin_password=None):
        s = self.session
        stmt = "SELECT EXISTS (SELECT FROM node)"
        nodes_exist = s.execute(stmt).fetchone()[0]
        if not nodes_exist:
            init_database_values(s, default_admin_password=default_admin_password)
            return True
        return False

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
        conn.execute(read_and_prepare_sql("node_funcs.sql"))
        conn.execute(read_and_prepare_sql("noderelation_funcs.sql"))
        conn.execute(read_and_prepare_sql("json.sql"))
        conn.execute(read_and_prepare_sql("nodesearch.sql"))
        conn.execute(read_and_prepare_sql("node_access_funcs.sql"))
        conn.execute(read_and_prepare_sql("node_access_rules_and_triggers.sql"))
        conn.execute(read_and_prepare_sql("noderelation_rules_and_triggers.sql"))

    def drop_functions(self, conn):
        pass

    def create_all(self):
        from sqlalchemy import orm
        orm.configure_mappers()
        with self.engine.begin() as conn:
            conn.execute("SET search_path TO " + self.metadata.schema)
            self.create_tables(conn)
            self.create_functions(conn)

    def drop_all(self):
        with self.engine.begin() as conn:
            conn.execute("SET search_path TO " + self.metadata.schema)
            self.drop_functions(conn)
            self.drop_tables(conn)

    def init_fulltext_search(self):
        from core.database.postgres.setting import Setting
        from core.database.postgres.search import fts_config_exists
        s = self.session
        autoindex_languages_from_config = [l.strip() for l in config.get("search.autoindex_languages", "").split(",") if l.strip()]
        autoindex_languages = []

        for lang in autoindex_languages_from_config:
            if fts_config_exists(lang):
                autoindex_languages.append(lang)
            else:
                logg.warn("postgres search config '%s' not found, ignored", lang)

        autoindex_languages_setting = Setting(key=u"search.autoindex_languages", value=autoindex_languages)
        s.merge(autoindex_languages_setting)
        s.commit()

    def run_psql_command(self, command, output=False, database=None):
        """Executes a single SQL command via an external psql call.
        Uses the connections options that are specified for the connector.
        :param output: Return output from psql invocation?
        :param database: override database name specified by connector configuration
        """
        return self._run_psql(database, output, "-c", command)

    def run_psql_file(self, filepath, output=False, database=None):
        """Executes a list of SQL statements from a file via an external psql call.
        Uses the connections options that are specified for the connector.
        :param output: Return output from psql invocation?
        :param database: override database name specified by connector configuration
        """
        return self._run_psql(database, output, "-f", filepath)

    def _run_psql(self, database, output, *additional_args):
        if database is None:
            database = self.database

        args = ["psql", "-tA", "-h", self.host, "-p", str(self.port), "-U", self.user, database]
        args.extend(additional_args)

        env = dict(os.environ, PGPASSWORD=self.passwd)

        if output:
            return check_output(args, env=env)
        else:
            check_call(args, env=env)

    # test helpers

    def disable_session_for_test(self):
        """Disables db.Session, preventing all session operations using db.session. Used for unit tests."""
        self._Session = self.Session
        self.Session = disabled_scoped_session

    def enable_session_for_test(self):
        """Reenables db.Session after disabling it with disable_session_for_test(),
        allowing session operations using db.session. Used for unit tests."""
        self.Session = self._Session
