# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop trigger in node_to_file

Revision ID: 73d8e632ec3a
Revises: e747587ee8a1
Create Date: 2018-10-29 15:01:41.329354

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = '73d8e632ec3a'
down_revision = 'e747587ee8a1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Drop trigger node_to_file_trigger on node_to_file for sqlalchemy-continuum 1.3.6
    op.execute('DROP TRIGGER node_to_file_trigger ON node_to_file')


def downgrade():
    # Create trigger node_to_file_trigger on node_to_file for sqlalchemy-continuum 1.2.4
    op.execute('CREATE TRIGGER node_to_file_trigger AFTER INSERT OR DELETE OR UPDATE ON node_to_file FOR EACH ROW EXECUTE PROCEDURE node_to_file_audit()')
