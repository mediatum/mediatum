"""add Node.system_attrs column

Revision ID: b8c946be109
Revises: 6e37c3bcacf
Create Date: 2015-11-23 16:18:08.767182

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = 'b8c946be109'
down_revision = '3ba37c887c16'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('node', sa.Column('system_attrs', postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column('node', 'system_attrs')
