"""delete unused postgres functions

Revision ID: a32ec9c3e5c5
Revises: 9588a1330308
Create Date: 2022-01-20 13:17:37.148719

"""

# revision identifiers, used by Alembic.
revision = 'a32ec9c3e5c5'
down_revision = '9588a1330308'
branch_labels = None
depends_on = None

import alembic as _alembic

_functions_to_delete = (
    "check_transitive_integrity",
    "compare_noderelation_with_backup",
    "create_attrindex_search",
    "drop_attrindex_search",
    "fix_transitive_integrity",
    "insert_node_tsvectors",
    "node_to_file_audit",
    "recreate_all_tsvectors_attrs",
    "recreate_all_tsvectors_fulltext",
    "update_node_tsvectors"
    )

def upgrade():
    for func in _functions_to_delete:
        _alembic.op.execute("DROP FUNCTION IF EXISTS {}".format(func));


def downgrade():
    pass
