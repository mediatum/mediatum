"""drop workflowstep checkcontent

Revision ID: ed88eef38764
Revises: 78e40e182e2f
Create Date: 2024-02-01 11:40:14.979474

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
from core.database.postgres import node as _postgres_node
# revision identifiers, used by Alembic.
revision = 'ed88eef38764'
down_revision = u'78e40e182e2f'


def upgrade():
    for node in _core.db.query(_postgres_node.Node).filter(
            _postgres_node.Node.type == 'workflowstep_checkcontent',
        ).prefetch_attrs():
        node.type = "workflowstep_textpage"
        node.set("text", "WARNING: Here should be a checkcontent workflowstep, but this type got removed.")
        node.settings = dict(htmltext="")
    _core.db.session.commit()


def downgrade():
    pass
