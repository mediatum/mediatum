"""Add private column and associated exclusion constraint to UserToUserGroup model
WARNING: this is only the schema migration. permission and user data is not correct after applying this!

Revision ID: 5888f47464a2
Revises: 8b9009f4e7a
Create Date: 2016-01-28 16:34:46.264155

"""

# revision identifiers, used by Alembic.
revision = '5888f47464a2'
down_revision = '8b9009f4e7a'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user_to_usergroup', sa.Column('private', sa.Boolean(), server_default='false', nullable=True))
    constraint_sql = "EXCLUDE USING btree (user_id WITH =) WHERE (private = true)"
    op.execute("ALTER TABLE mediatum.user_to_usergroup ADD CONSTRAINT only_one_private_group_per_user " + constraint_sql)


def downgrade():
    op.drop_column('user_to_usergroup', 'private')
    op.execute("ALTER TABLE mediatum.user_to_usergroup DROP CONSTRAINT only_one_private_group_per_user")