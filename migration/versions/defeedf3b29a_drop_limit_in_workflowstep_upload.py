# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_limit_in_workflowstep_upload

Revision ID: defeedf3b29a
Revises: 65da41555319
Create Date: 2022-11-18 09:10:26.730772

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
from core.database.postgres.node import Node

# revision identifiers, used by Alembic.
revision = 'defeedf3b29a'
down_revision = u'65da41555319'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_upload').prefetch_attrs():
        node.attrs.pop("limit", None)
    _core.db.session.commit()

def downgrade():
    pass
