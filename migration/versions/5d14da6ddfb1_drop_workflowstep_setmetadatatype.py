# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_workflowstep_setmetadatatype

Revision ID: 5d14da6ddfb1
Revises: 190fd45cc2b0
Create Date: 2026-02-12 16:56:41.033886

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
import core.database.postgres.node as _
import core.init as _
_core.init.full_init()

# revision identifiers, used by Alembic.
revision = '5d14da6ddfb1'
down_revision = u'190fd45cc2b0'
branch_labels = None
depends_on = None


def upgrade():
    Node = _core.database.postgres.node.Node
    wfstepids = set()
    for wfstep in _core.db.query(Node).filter(Node.type == 'workflowstep_setmetadatatype').prefetch_attrs():
        wfstep.type = "workflowstep_replacenodemetadatatype"
        wfstepids.add(wfstep.id)
    _core.db.session.commit()
    for wfstep in map(_core.db.query(Node).get, wfstepids):
        settings = wfstep.settings
        settings.pop("clear-files", None)
        settings["id-attribute"] = None
        wfstep.settings = settings
    _core.db.session.commit()


def downgrade():
    Node = _core.database.postgres.node.Node
    for wfstep in _core.db.query(Node).filter(Node.type == 'workflowstep_replacenodemetadatatype').prefetch_attrs():
        wfstep.type = "workflowstep_setmetadatatype"
        settings = wfstep.settings
        settings.pop("id-attribute", None)
        settings["clear-files"] = True
        wfstep.settings = settings
    _core.db.session.commit()
