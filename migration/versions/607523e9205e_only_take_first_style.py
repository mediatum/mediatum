# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""only take first style

Revision ID: 607523e9205e
Revises: 01bd03643404
Create Date: 2022-11-30 12:59:52.428699

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
revision = '607523e9205e'
down_revision = u'01bd03643404'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(_postgres_node.Node).filter(_postgres_node.Node.a['style'].isnot(None)).all():
        node.attrs['style'] = node.attrs['style'].split(';', 1)[0]

    _core.db.session.commit()


def downgrade():
    pass
