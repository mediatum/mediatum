# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop workflowstep condition

Revision ID: cd83ccfac946
Revises: 00cd2f72a4b8
Create Date: 2025-07-28 16:38:04.839876

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
import core.database as _
import core.database.postgres as _
import core.database.postgres.node as _
import workflow as _workflow
import workflow.textpage as _

# revision identifiers, used by Alembic.
revision = 'cd83ccfac946'
down_revision = u'00cd2f72a4b8'
branch_labels = None
depends_on = None


def upgrade():
    Node = _core.database.postgres.node.Node
    for wfstepid, in _core.db.query(Node).filter(Node.type=='workflowstep_condition').values(Node.id):
        _core.db.query(Node).get(wfstepid).type = "workflowstep_textpage"
        _core.db.session.commit()
        wfstep = _core.db.query(Node).get(wfstepid)
        wfstep.set("alembic-{}".format(revision), wfstep.get("workflowstep-settings"))
        wfstep.set("text", "WARNING: Here should be a condition workflowstep, but this type got removed.")
        wfstep.settings = dict(htmltext="")
    _core.db.session.commit()


def downgrade():
    WorkflowStep_TextPage = _workflow.textpage.WorkflowStep_TextPage
    alembic_revision = "alembic-{}".format(revision)
    for wfstep in (_core.db.query(WorkflowStep_TextPage)
                 .filter(WorkflowStep_TextPage.attrs[alembic_revision].astext!="")
                 .prefetch_attrs()
    ):
        wfstep.type = "workflowstep_condition"
        wfstep.set("workflowstep-settings", wfstep.attrs.pop(alembic_revision))
        del wfstep.attrs["text"]
    _core.db.session.commit()

