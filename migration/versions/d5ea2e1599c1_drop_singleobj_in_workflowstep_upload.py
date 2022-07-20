# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_singleobj_in_workflowstep_upload

Revision ID: d5ea2e1599c1
Revises: 70c1f0f66285
Create Date: 2022-07-20 14:32:08.602199

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
revision = 'd5ea2e1599c1'
down_revision = u'70c1f0f66285'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(_core.Node).filter(_core.Node.type == 'workflowstep_upload').prefetch_attrs():
        node.attrs.pop("singleobj", None)
    _core.db.session.commit()


def downgrade():
    pass
