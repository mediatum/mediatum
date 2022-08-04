# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_workflowstep_fileattachment

Revision ID: 975b96703a01
Revises: 7e8416106379
Create Date: 2022-10-06 06:18:48.008288

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

revision = '975b96703a01'
down_revision = u'7e8416106379'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_fileattachment').prefetch_attrs():
        node.type = "workflowstep_editmetadata"
        node.attrs["mask"] = node.attrs.pop("mask_fileatt", "")
        for f in node.files:
            node.files.remove(f)
    _core.db.session.commit()


def downgrade():
    pass
