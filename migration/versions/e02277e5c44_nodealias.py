# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""add table for NodeAlias model

Revision ID: e02277e5c44
Revises: 58dc49ab4fc8
Create Date: 2015-11-19 16:03:06.121609

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = 'e02277e5c44'
down_revision = '58dc49ab4fc8'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('node_alias',
    sa.Column('alias', sa.Unicode(), nullable=False),
    sa.Column('nid', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['nid'], [u'mediatum.node.id'], ),
    sa.PrimaryKeyConstraint('alias'),
    schema='mediatum'
    )


def downgrade():
    op.drop_table('node_alias', schema='mediatum')