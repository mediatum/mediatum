# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""workflowstep_start_convert_schemas_to_tuples

Revision ID: df6f5dab2877
Revises: ab6e1ab42b57
Create Date: 2022-12-08 06:41:30.248745

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

import workflow.start as _start


# revision identifiers, used by Alembic.
revision = 'df6f5dab2877'
down_revision = u'ab6e1ab42b57'
branch_labels = None
depends_on = None


def upgrade():
    for workflowstep in _core.db.query(_start.WorkflowStep_Start).prefetch_attrs():
        settings = workflowstep.settings
        settings["schemas"] = [s.split('/') for s in settings["schemas"]]
        workflowstep.settings = settings
    _core.db.session.commit()


def downgrade():
    for workflowstep in _core.db.query(_start.WorkflowStep_Start).prefetch_attrs():
        settings = workflowstep.settings
        settings["schemas"] = ['/'.join(s) for s in settings["schemas"]]
        workflowstep.settings = settings
    _core.db.session.commit()
