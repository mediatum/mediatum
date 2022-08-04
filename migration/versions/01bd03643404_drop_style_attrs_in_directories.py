# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_style_attrs_in_directories

Revision ID: 01bd03643404
Revises: 04ca61e54c2d
Create Date: 2023-03-23 15:57:26.184738

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
import contenttypes as _contenttypes

# revision identifiers, used by Alembic.
revision = '01bd03643404'
down_revision = u'04ca61e54c2d'
branch_labels = None
depends_on = None


def upgrade():
    for directory in _core.db.query(_contenttypes.Directory).prefetch_attrs():
        directory.attrs.pop("style", None)
        directory.attrs.pop("style_full", None)
    _core.db.session.commit()


def downgrade():
    pass
