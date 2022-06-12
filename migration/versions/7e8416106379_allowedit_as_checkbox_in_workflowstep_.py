# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""allowedit_as_checkbox_in_workflowstep_sendemail

Revision ID: 7e8416106379
Revises: 61e68c44d0b3
Create Date: 2022-07-20 15:29:37.243846

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

# revision identifiers, used by Alembic.
revision = '7e8416106379'
down_revision = u'61e68c44d0b3'
branch_labels = None
depends_on = None

def upgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_sendemail').prefetch_attrs():
        if node.get("allowedit", "n").lower().startswith("n"):
            node.attrs.pop("allowedit", None)
        else:
            node.set("allowedit", "1")
    _core.db.session.commit()


def downgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_sendemail').prefetch_attrs():
        node.set("allowedit", "Ja" if node.get("allowedit") else "Nein")
    _core.db.session.commit()
