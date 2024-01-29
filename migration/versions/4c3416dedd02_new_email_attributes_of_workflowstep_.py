# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""new email attributes of workflowstep settings
    sender - > from_email
    new from_name
    new from_envelope
    new reply_to_email
    new reply_to_name

Revision ID: 4c3416dedd02
Revises: 8c38553b854a
Create Date: 2023-12-04 07:40:40.879074

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import json as _json

import core as _core
import core.init as _core_init
_core_init.full_init()
import workflow.email as _workflow_email
# revision identifiers, used by Alembic.
revision = '4c3416dedd02'
down_revision = u'8c38553b854a'


def upgrade():
    for workflowstep in _core.db.query(_workflow_email.WorkflowStep_SendEmail).prefetch_attrs():
        settings = workflowstep.default_settings
        settings.update(workflowstep.settings)
        settings["from_email"] = settings.pop("sender", workflowstep.default_settings["from_email"])
        workflowstep.settings = settings

    _core.db.session.commit()


def downgrade():
    for workflowstep in _core.db.query(_workflow_email.WorkflowStep_SendEmail).prefetch_attrs():
        settings = workflowstep.settings
        settings["sender"] = settings.pop("from_email")
        settings.pop("from_name")
        settings.pop("from_envelope")
        settings.pop("reply_to_email")
        settings.pop("reply_to_name")
        workflowstep.settings = settings

    _core.db.session.commit()
