# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_sendcondition in workflowstep_sendemail

Revision ID: 95100016941a
Revises: a1c9f3a042ad
Create Date: 2022-07-20 09:37:03.924488

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
revision = '95100016941a'
down_revision = u'a1c9f3a042ad'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_sendemail').prefetch_attrs():
        node.attrs.pop("sendcondition", None)
    _core.db.session.commit()


def downgrade():
    pass
