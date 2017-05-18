"""create file hashes sha512

Revision ID: 4df503937ab1
Revises: 3296a17debd3
Create Date: 2017-01-11 16:34:07.472179

"""

# revision identifiers, used by Alembic.
revision = '4df503937ab1'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy_continuum.dialects.postgresql import sync_trigger


def upgrade():
    for table in ['file', 'file_version']:
        op.add_column(table, sa.Column('sha512',
                                        sa.String(length=128),
                                        server_default=None,
                                        nullable=True))
        op.add_column(table, sa.Column('sha512_checked_at',
                                        sa.DateTime(),
                                        server_default=None,
                                        nullable=True))
        op.add_column(table, sa.Column('sha512_created_at',
                                        sa.DateTime(),
                                        server_default=None,
                                        nullable=True))
        op.add_column(table, sa.Column('sha512_ok',
                                        sa.Boolean(),
                                        server_default=None,
                                        nullable=True))
        # file size
        op.add_column(table, sa.Column('size',
                                        sa.BigInteger(),
                                        server_default=None,
                                        nullable=True))
    # sync triggers, for explanation see
    # http://sqlalchemy-continuum.readthedocs.io/en/latest/native_versioning.html
    # careful works only with our fork of sqlalchemy-continuum because of #115
    # https://github.com/kvesteri/sqlalchemy-continuum/issues/115
    conn = op.get_bind()
    sync_trigger(conn, 'file_version')



def downgrade():
    for table in ['file', 'file_version']:
        op.drop_column(table, 'sha512')
        op.drop_column(table, 'sha512_created_at')
        op.drop_column(table, 'sha512_checked_at')
        op.drop_column(table, 'sha512_ok')
        # file size
        op.drop_column(table, 'size')
    conn = op.get_bind()
    sync_trigger(conn, 'file_version')
