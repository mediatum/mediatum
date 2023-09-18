# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop metafield hlist

Revision ID: b0dfcab84653
Revises: 0bce7f5bc04d
Create Date: 2023-08-01 07:54:57.578441

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
revision = 'b0dfcab84653'
down_revision = u'0bce7f5bc04d'
branch_labels = None
depends_on = None

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
from core import init as _core_init
_core_init.full_init()
from schema import schema as _schema


def upgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == 'hlist').prefetch_attrs():
        metafield.attrs['type'] = u'text'
    _core.db.session.commit()


def downgrade():
    pass
