# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_prefix_suffix_in_workflowstep_upload

Revision ID: 70c1f0f66285
Revises: 95100016941a
Create Date: 2022-07-20 14:16:23.096617

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

# revision identifiers, used by Alembic.
revision = '70c1f0f66285'
down_revision = u'95100016941a'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(_core.Node).filter(_core.Node.type == 'workflowstep_upload').prefetch_attrs():
        node.attrs.pop("prefix", None)
        node.attrs.pop("suffix", None)
    _core.db.session.commit()


def downgrade():
    pass
