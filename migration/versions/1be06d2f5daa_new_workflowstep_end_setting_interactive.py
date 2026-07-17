# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""new workflowstep end setting interactive

Revision ID: 1be06d2f5daa
Revises: aa19d5c8c132
Create Date: 2026-07-17 17:32:52.602214

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.database.postgres.node as _
import core.init as _
import workflow as _workflow
import workflow.end as _

# revision identifiers, used by Alembic.
revision = '1be06d2f5daa'
down_revision = u'aa19d5c8c132'
branch_labels = None
depends_on = None

_logg = _logging.getLogger(__name__)


def upgrade():
    _core.init.basic_init()
    for end_step in _core.db.query(_workflow.end.WorkflowStep_End).prefetch_attrs():
        end_step.settings = dict(end_step.default_settings, **end_step.settings)
    _core.db.session.commit()


def downgrade():
    _core.init.basic_init()
    for end_step in _core.db.query(_workflow.end.WorkflowStep_End).prefetch_attrs():
        settings = end_step.settings
        settings.pop("interactive", None)
        end_step.settings = settings
    _core.db.session.commit()
