# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""metafield_text_add_pattern

Revision ID: c7b29bc0e141
Revises: cd83ccfac946
Create Date: 2025-12-05 10:54:17.535436

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
import core.init as _
_core.init.full_init()
import schema.schema as _schema

# revision identifiers, used by Alembic.
revision = 'c7b29bc0e141'
down_revision = u'cd83ccfac946'
branch_labels = None
depends_on = None


def upgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == 'text').prefetch_attrs():
        data = metafield.metatype_data or {}
        data["pattern"] = ".*"
        metafield.metatype_data = data
    _core.db.session.commit()


def downgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == 'text').prefetch_attrs():
        data = metafield.metatype_data
        data.pop("pattern", None)
        metafield.metatype_data = data
    _core.db.session.commit()
