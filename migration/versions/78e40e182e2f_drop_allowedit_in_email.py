"""drop allowedit in email

Revision ID: 78e40e182e2f
Revises: 4c3416dedd02
Create Date: 2024-01-29 12:27:18.547409

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import functools as _functools
import json as _json
import os as _os

import core as _core
import core.init as _core_init
_core_init.full_init()
import workflow.email as _workflow_email
from utils import utils as _utils_utils
# revision identifiers, used by Alembic.
revision = '78e40e182e2f'
down_revision = u'4c3416dedd02'
branch_labels = None
depends_on = None


def upgrade():
    for workflowstep in _core.db.query(_workflow_email.WorkflowStep_SendEmail).prefetch_attrs():
        workflowstep.attrs.pop("allowedit", None)
    _core.db.session.commit()


def downgrade():
    for workflowstep in _core.db.query(_workflow_email.WorkflowStep_SendEmail).prefetch_attrs():
        workflowstep.attrs["allowedit"] = False
    _core.db.session.commit()
