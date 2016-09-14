"""add table for NodeType model

Revision ID: 58dc49ab4fc8
Revises: 4dd3472f0d22
Create Date: 2015-11-10 19:50:54.663015

"""

# revision identifiers, used by Alembic.
revision = '58dc49ab4fc8'
down_revision = '4dd3472f0d22'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('nodetype',
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('is_container', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('name'),
    schema='mediatum'
    )
    op.create_index(op.f('ix_mediatum_nodetype_is_container'), 'nodetype', ['is_container'], unique=False, schema='mediatum')


def downgrade():
    op.drop_index(op.f('ix_mediatum_nodetype_is_container'), table_name='nodetype', schema='mediatum')
    op.drop_table('nodetype', schema='mediatum')
