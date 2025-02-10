# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os.path
import urllib as _urllib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy_continuum.utils import version_class

import core as _core
import core.database.postgres.node as _
from core import config
from . import db_metadata, DeclarativeBase
from utils.postgres import schema_exists, table_exists
import utils.process
import sys
from core.search.config import get_fulltext_autoindex_languages, get_attribute_autoindex_languages


CONNECTSTR_TEMPLATE = "postgresql+psycopg2://{user}:{passwd}@:{port}/{database}"
CONNECTSTR_TEMPLATE_WITHOUT_PW = "postgresql+psycopg2://{user}@:{port}/{database}"

logg = logging.getLogger(__name__)


def read_and_prepare_sql(sql_filepath, sql_dir=None):
    """
    Reads SQL code from a file, sets search path
    """
    if sql_dir is None:
        sql_dir = os.path.join(os.path.dirname(__file__), "sql")

    with open(os.path.join(sql_dir, sql_filepath)) as f:
        sql = f.read().replace(":search_path", "mediatum").replace("%", "%%")

    return sql


def disabled_scoped_session(*args, **kwargs):
    raise Exception("Test mode, database session disabled. Use the core.test.fixtures.session fixture!")


class ConnectionException(Exception):
    pass


class PostgresSQLAConnector(object):

    """Basic db object used by the application
    """

    def __init__(self):
        session_factory = sessionmaker(query_cls=_core.database.postgres.node.MtQuery)
        self.Session = scoped_session(session_factory)
        self.metadata = db_metadata

    def configure(self):
        self.host = config.get("database.host", "localhost")
        self.port = config.getint("database.port", "5432")
        self.database = config.get("database.db", "mediatum")
        self.user = config.get("database.user", "mediatum")
        self.passwd = config.get("database.passwd")
        self.pool_size = config.getint("database.pool_size", 20)
        if self.passwd:
            self.passwd = _urllib.quote_plus(self.passwd)
            self.connectstr = CONNECTSTR_TEMPLATE.format(**self.__dict__)
        else:
            self.connectstr = CONNECTSTR_TEMPLATE_WITHOUT_PW.format(**self.__dict__)
        logg.info("using database connection string: %s", CONNECTSTR_TEMPLATE_WITHOUT_PW.format(**self.__dict__))

    def create_engine(self):
        connect_args = dict(
            host=self.host,
            application_name="{}({})".format(os.path.basename(sys.argv[0]), os.getpid())
        )

        engine = create_engine(self.connectstr, connect_args=connect_args, pool_size=self.pool_size)
        db_connection_exception = self.check_db_connection(engine)

        if db_connection_exception:
            msg = "Could not connect to database, error was: " + db_connection_exception.args[0]
            if config.is_default_config:
                msg += """
                    HINT: You are running mediaTUM without a config file. Did you forget to create one?
                    \nSee --help for more info.
                    """
            else:
                msg += "check the settings in the [database] section in your config file."

            raise ConnectionException(msg)

        DeclarativeBase.metadata.bind = engine
        self.engine = engine
        self.Session.configure(bind=engine)

    def check_db_connection(self, engine):
        try:
            conn = engine.connect()
        except Exception as e:
            return e

        res = conn.execute("SELECT version()")
        version = res.fetchone()
        res = conn.execute("SHOW search_path")
        search_path = res.fetchone()
        logg.info("db connection test succeeded, search_path is '%s', version is: '%s'", search_path[0], version[0])
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

        core.db.query(Node).get(42)
        """
        return self.Session().query(*entities, **kwargs)

    def refresh(self, node):
        """Return a refreshed copy of `node`.
        Workaround for Node objects which are kept between requests.
        XXX: must be removed later
        """
        NodeVersion = version_class(_core.database.postgres.node.Node)
        if isinstance(node, NodeVersion):
            return self.session.query(NodeVersion).get((node.id, node.transaction.id))
        else:
            return self.session.query(_core.database.postgres.node.Node).get(node.id)

    # database manipulation helpers

    def drop_schema(self):
        if schema_exists(self.session, "mediatum"):
            self.session.execute("DROP SCHEMA mediatum CASCADE")
            self.session.commit()
            logg.info("dropped database structure")
        else:
            logg.info("schema mediatum does not exist, cannot drop it")

    def create_schema(self, set_alembic_version=True):
        """Creates the 'mediatum' schema.
        :param set_alembic_version: Stamp database with current alembic revision information. Defaults to True.
        Can be disabled if a schema for testing is going to be created.
        """
        logg.info("creating DB schema...")
        self.session.execute("CREATE SCHEMA mediatum")
        self.session.commit()
        try:
            self.create_all()
            if set_alembic_version:
                # create alembic version table and set current alembic version to head
                from alembic.config import Config
                from alembic import command
                alembic_cfg = Config(os.path.join(config.basedir, "alembic.ini"))
                alembic_cfg.attributes["running_in_mediatum"] = True
                command.stamp(alembic_cfg, "head")
            self.session.commit()
            logg.info("commited database structure")
        except:
            # I tried to use a transaction to enclose everything, but sqlalchemy (?) fails when the schema is created within the transaction
            # solution: just drop the schema it if something fails after schema creation
            self.session.execute("DROP SCHEMA mediatum CASCADE")
            raise

    def upgrade_schema(self):
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(config.basedir, "alembic.ini"))
        alembic_cfg.attributes["running_in_mediatum"] = True
        command.upgrade(alembic_cfg, "head")

    def create_tables(self, conn):
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
        conn.execute(read_and_prepare_sql("speedups.sql"))

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

        fulltext_autoindex_languages = get_fulltext_autoindex_languages()

        if fulltext_autoindex_languages:
            fulltext_autoindex_languages_setting = Setting(key=u"search.fulltext_autoindex_languages", value=list(fulltext_autoindex_languages))
            self.session.merge(fulltext_autoindex_languages_setting)

        attribute_autoindex_languages = get_attribute_autoindex_languages()

        if attribute_autoindex_languages:
            attribute_autoindex_languages_setting = Setting(key=u"search.attribute_autoindex_languages", value=list(attribute_autoindex_languages))
            self.session.merge(attribute_autoindex_languages_setting)

        self.session.commit()

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
            return utils.process.check_output(args, env=env)
        else:
            utils.process.check_call(args, env=env)

    # test helpers

    def disable_session_for_test(self):
        """Disables db.Session and closes the current session, preventing all session operations using db.session. Used for unit tests."""
        self.Session.remove()
        self._Session = self.Session
        self.Session = disabled_scoped_session

    def enable_session_for_test(self):
        """Reenables db.Session after disabling it with disable_session_for_test(),
        allowing session operations using db.session. Used for unit tests."""
        self.Session = self._Session
