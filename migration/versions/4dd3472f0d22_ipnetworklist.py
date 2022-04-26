"""add table for IPNetworkList model

Revision ID: 4dd3472f0d22
Revises:
Create Date: 2015-11-09 13:26:00.538227

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = '4dd3472f0d22'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('ipnetwork_list',
    sa.Column('name', sa.Unicode(), nullable=False),
    sa.Column('description', sa.Unicode(), nullable=True),
    sa.Column('subnets', postgresql.ARRAY(postgresql.CIDR()), nullable=True),
    sa.PrimaryKeyConstraint('name'),
    schema='mediatum'
    )
    op.create_index(op.f('ix_mediatum_ipnetwork_list_subnets'), 'ipnetwork_list', ['subnets'], unique=False, schema='mediatum')


def downgrade():
    op.drop_table('ipnetwork_list', schema='mediatum')