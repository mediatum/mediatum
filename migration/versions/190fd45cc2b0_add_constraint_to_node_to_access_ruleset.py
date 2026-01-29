# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""add_constraint_to_node_to_access_ruleset

Revision ID: 190fd45cc2b0
Revises: c7b29bc0e141
Create Date: 2026-01-29 13:32:08.223674

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import alembic as _alembic

# revision identifiers, used by Alembic.
revision = '190fd45cc2b0'
down_revision = u'c7b29bc0e141'
branch_labels = None
depends_on = None


def upgrade():
    _alembic.op.execute('''
        ALTER TABLE node_to_access_ruleset
        ADD CONSTRAINT distinct_private_ruleset_name EXCLUDE (ruleset_name WITH =) WHERE (private)
        ''')


def downgrade():
    _alembic.op.execute('ALTER TABLE node_to_access_ruleset DROP CONSTRAINT distinct_private_ruleset_name')
