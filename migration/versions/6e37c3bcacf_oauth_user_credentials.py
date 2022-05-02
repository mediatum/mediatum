"""add table for OAuthUserCredentials model

Revision ID: 6e37c3bcacf
Revises: e02277e5c44
Create Date: 2015-12-10 15:39:17.947589

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = '6e37c3bcacf'
down_revision = 'e02277e5c44'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('oauth_user_credentials',
    sa.Column('oauth_user', sa.Unicode(), nullable=False),
    sa.Column('oauth_key', sa.Unicode(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], [u'mediatum.user.id'], ),
    sa.PrimaryKeyConstraint('oauth_user'),
    schema='mediatum'
    )


def downgrade():
    op.drop_table('oauth_user_credentials', schema='mediatum')