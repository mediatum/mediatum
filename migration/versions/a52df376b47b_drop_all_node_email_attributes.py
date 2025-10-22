# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop all node's email attributes

Revision ID: a52df376b47b
Revises: 0bcb4393aeb6
Create Date: 2023-11-27 12:57:04.436860

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import sys as _sys

# revision identifiers, used by Alembic.
revision = 'a52df376b47b'
down_revision = u'0bcb4393aeb6'
branch_labels = None
depends_on = None

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.database as _
import core.database.postgres as _
import core.database.postgres.node as _
from core import init as _core_init
_core_init.full_init()


def upgrade():
    Node = _core.database.postgres.node.Node
    for node in _core.db.query(Node).filter(Node.system_attrs['mailtmp.from'] != None).all():
        node.system_attrs.pop("mailtmp.from")
        node.system_attrs.pop("mailtmp.to", None)
        node.system_attrs.pop("mailtmp.subject", None)
        node.system_attrs.pop("mailtmp.text", None)
        node.system_attrs.pop("mailtmp.error",None)

    _core.db.session.commit()


def downgrade():
    pass
