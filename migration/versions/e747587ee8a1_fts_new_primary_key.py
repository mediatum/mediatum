"""fts new primary key

Revision ID: e747587ee8a1
Revises: 4df503937ab1
Create Date: 2018-07-23 07:09:17.595063

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = 'e747587ee8a1'
down_revision = '4df503937ab1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Drop primary key constraint. Note the CASCASE clause - this deletes the foreign key constraint.
    op.execute('ALTER TABLE fts DROP CONSTRAINT fts_pkey CASCADE')
    # Re-create the primary key constraint
    op.create_primary_key('fts_pkey', 'fts', ['nid','config','searchtype'])

def downgrade():
    # Drop primary key constraint. Note the CASCASE clause - this deletes the foreign key constraint.
    op.execute('ALTER TABLE fts DROP CONSTRAINT fts_pkey CASCADE')
    # Re-create the primary key constraint
    op.create_primary_key('fts_pkey', 'fts', ['id'])
