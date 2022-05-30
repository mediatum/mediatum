# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import with_statement, print_function

import os.path as _os_path
import sys
from alembic import context
from logging.config import fileConfig
import sqlalchemy.orm

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

sys.path.append(_os_path.normpath(_os_path.join(__file__, "..", "..")))

# Don't run DB initialization when we are running alembic commands from within the mediaTUM process.
if not config.attributes.get("running_in_mediatum"):
    # Interpret the config file for Python logging.
    # This line sets up loggers basically.
    fileConfig(config.config_file_name)

    from core import init
    init.basic_init()

    sqlalchemy.orm.configure_mappers()

from core import db
from core.database.postgres import DB_SCHEMA_NAME

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return object.schema == DB_SCHEMA_NAME
    else:
        return object.table.schema == DB_SCHEMA_NAME


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    with db.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=db.metadata,
            version_table_schema=DB_SCHEMA_NAME,
            include_schemas=True,
            include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    raise NotImplementedError("cannot be used in offline mode at the moment")
else:
    run_migrations_online()
