# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""directly set TAL for sender in workflowstep-settings

Revision ID: 8c38553b854a
Revises: a52df376b47b
Create Date: 2023-11-30 10:11:12.371939

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
import core.init as _core_init
_core_init.full_init()
import workflow.email as _workflow_email
from utils import utils as _utils_utils
# revision identifiers, used by Alembic.
revision = '8c38553b854a'
down_revision = u'a52df376b47b'


def _put_TAL(address):
    if "@" not in address:
        return '''<tal:block tal:replace="raw python:node.get('{}')"/>'''.format(
            _utils_utils.esc(address),
        )
    return address


def upgrade():
    for workflowstep in _core.db.query(_workflow_email.WorkflowStep_SendEmail).prefetch_attrs():
        settings = workflowstep.settings
        settings["sender"] = _put_TAL(settings["sender"])
        settings["recipient"] = list(map(_put_TAL, settings["recipient"]))
        workflowstep.settings = settings
    _core.db.session.commit()


def downgrade():
    pass
