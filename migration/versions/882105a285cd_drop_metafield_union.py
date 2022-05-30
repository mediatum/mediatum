# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop metafield union

Revision ID: 882105a285cd
Revises: f543090df491
Create Date: 2021-03-09 09:40:34.978921

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = '882105a285cd'
down_revision = 'f543090df491'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
import schema.schema as _schema

_q = _core.db.query

def upgrade():
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'union').prefetch_attrs():
        metafield.attrs['type'] = u'text'
    _core.db.session.commit()


def downgrade():
    pass
