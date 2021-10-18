"""delete column can_edit_shoppingbag

Revision ID: 79cc3a51f0ac
Revises: 882105a285cd
Create Date: 2021-10-15 06:13:32.611937

"""

# revision identifiers, used by Alembic.
revision = '79cc3a51f0ac'
down_revision = '882105a285cd'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()

from core import User

import sqlalchemy as _sqlalchemy

import sqlalchemy_continuum as _sqlalchemy_continuum


def upgrade():
    # if a new database is created the function user_audit for the trigger user_trigger
    # is automatically created by sqlalchemy continuum by the function create_versioning_trigger_listeners
    # in sqlalchemy_continuum/dialects/postgresql.py
    # if a column is added or deleted sqlalchemy continuum only offers the function
    # sync_trigger in sqlalchemy_continuum/dialects/postgresql.py to update this function.
    # but the sync_trigger function does not create the function user_audit in the same way as it
    # is done by the function create_versioning_trigger_listeners
    #
    # the main differences are:
    # 1.create_versioning_trigger_listeners calls also the function for_manager which is responsible for the
    #   block UPDATE mediatum.user_version in the user_audit function
    #   sync_trigger does not call for_manager so this block in the user_audit function is not created
    #
    # 2.sync_trigger calls the function create_trigger which sets the parameter use_property_mod_tracking
    #   to true
    #   create_versioning_trigger_listeners sets the parameter use_property_mod_tracking to false.
    #
    # so the creation of the function user_audit is called in the same was as the
    # function create_versioning_trigger_listeners
    _core.db.session.execute(str(_sqlalchemy_continuum.dialects.postgresql.CreateTriggerFunctionSQL.for_manager(_sqlalchemy_continuum.versioning_manager, User)))
    _core.db.session.execute("ALTER TABLE mediatum.user DROP COLUMN can_edit_shoppingbag")
    _core.db.session.commit()


def downgrade():
    # add column can_edit_shoppingbag to table user
    # see comment in upgrade()
    col = _sqlalchemy.Column('can_edit_shoppingbag', _sqlalchemy.BOOLEAN, default=False)
    _core.database.postgres.db_metadata.tables['mediatum.user']._columns.add(col)
    _core.db.session.execute("ALTER TABLE mediatum.user ADD COLUMN can_edit_shoppingbag boolean DEFAULT false")
    # add can_edit_shoppingbag in function user_audit
    _core.db.session.execute(str(_sqlalchemy_continuum.dialects.postgresql.CreateTriggerFunctionSQL.for_manager(_sqlalchemy_continuum.versioning_manager, User)))
    _core.db.session.commit()
