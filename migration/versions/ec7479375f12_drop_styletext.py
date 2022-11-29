# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop styletext

Revision ID: ec7479375f12
Revises: 607523e9205e
Create Date: 2022-12-08 06:44:59.566952

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
from core import init as _core_init
_core_init.full_init()
from core.database.postgres import node as _postgres_node

# revision identifiers, used by Alembic.
revision = 'ec7479375f12'
down_revision = u'607523e9205e'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(_postgres_node.Node).filter(_postgres_node.Node.a['style'] == "text").all():
        node.attrs.pop("style")

    _core.db.session.commit()


def downgrade():
    pass
