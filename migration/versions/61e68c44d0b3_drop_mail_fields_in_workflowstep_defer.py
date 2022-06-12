# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_mail_fields_in_workflowstep_defer

Revision ID: 61e68c44d0b3
Revises: d5ea2e1599c1
Create Date: 2022-07-20 14:59:21.327918

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
revision = '61e68c44d0b3'
down_revision = u'd5ea2e1599c1'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_defer').prefetch_attrs():
        node.attrs.pop("recipient", None)
        node.attrs.pop("subject", None)
        node.attrs.pop("body", None)
    _core.db.session.commit()


def downgrade():
    pass
