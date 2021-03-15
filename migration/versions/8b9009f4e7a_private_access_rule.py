"""Add private column and associated exclusion constraint to NodetoAccessRuleset model

Revision ID: 8b9009f4e7a
Revises: b8c946be109
Create Date: 2016-01-28 15:19:58.366190

"""

# revision identifiers, used by Alembic.
from __future__ import division

revision = '8b9009f4e7a'
down_revision = 'b8c946be109'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('node_to_access_ruleset', sa.Column('private', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('node_to_access_ruleset_version', sa.Column('private', sa.Boolean(), server_default='false', autoincrement=False, nullable=True))
    constraint_sql = "EXCLUDE USING btree (nid WITH =, ruletype WITH =) WHERE (private = true)"
    op.execute("ALTER TABLE mediatum.node_to_access_ruleset ADD CONSTRAINT only_one_private_ruleset_per_node_and_ruletype " + constraint_sql)


def downgrade():
    op.drop_column('node_to_access_ruleset', 'private')
    op.drop_column('node_to_access_ruleset_version', 'private')
    op.execute("ALTER TABLE mediatum.node_to_access_ruleset DROP CONSTRAINT only_one_private_ruleset_per_node_and_ruletype")