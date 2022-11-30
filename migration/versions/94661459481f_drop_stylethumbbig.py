# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop stylethumbbig

Revision ID: 94661459481f
Revises: ec7479375f12
Create Date: 2022-12-08 07:05:07.117409

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
revision = '94661459481f'
down_revision = u'ec7479375f12'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(_postgres_node.Node).filter(_postgres_node.Node.a['style'] == "thumbnailbig").all():
        node.attrs.pop("style")

    _core.db.session.commit()


def downgrade():
    pass
