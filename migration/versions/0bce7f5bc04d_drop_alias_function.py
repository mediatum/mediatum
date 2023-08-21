# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop alias function

Revision ID: 0bce7f5bc04d
Revises: bd53a7aeaae8
Create Date: 2022-12-21 11:58:52.401090

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import alembic as _alembic
import sqlalchemy as _sqlalchemy

# revision identifiers, used by Alembic.
revision = '0bce7f5bc04d'
down_revision = u'bd53a7aeaae8'
branch_labels = None
depends_on = None


def upgrade():
    _alembic.op.get_bind().execute(_sqlalchemy.text("DELETE FROM mediatum.node_alias"))


def downgrade():
    pass
