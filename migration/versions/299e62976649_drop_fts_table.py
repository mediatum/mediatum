"""drop fts table

Revision ID: 299e62976649
Revises: 6cd40ed911a7
Create Date: 2019-09-26 13:06:04.824965

"""

# revision identifiers, used by Alembic.
revision = '299e62976649'
down_revision = '6cd40ed911a7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # remove constraint fts_nid_fkey
    op.execute('ALTER TABLE fts DROP CONSTRAINT fts_nid_fkey CASCADE')
    # fts table is no longer used, for downgrad reason table fts is not dropped but renamed
    op.execute('ALTER TABLE fts RENAME TO fts_bak')
    # drop triggers insert_node_tsvectors, update_node_tsvectors which are useless without table fts
    op.execute('DROP TRIGGER insert_node_tsvectors ON node');
    op.execute('DROP TRIGGER update_node_tsvectors ON node');


def downgrade():
    # restore table fts from fts_bak
    op.execute('ALTER TABLE fts_bak RENAME TO fts')
    # add constraint fts_nid_fkey
    op.execute('ALTER TABLE fts ADD CONSTRAINT fts_nid_fkey FOREIGN KEY (nid) REFERENCES node(id) ON DELETE CASCADE')
    # create triggers for table node to write changes in table fts
    op.execute('CREATE TRIGGER insert_node_tsvectors AFTER INSERT ON node FOR EACH ROW EXECUTE PROCEDURE insert_node_tsvectors()')
    op.execute('CREATE TRIGGER update_node_tsvectors AFTER UPDATE ON node FOR EACH ROW EXECUTE PROCEDURE update_node_tsvectors()')
