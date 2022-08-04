# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_workflowstep_addtofolder

Revision ID: a1c9f3a042ad
Revises: 94661459481f
Create Date: 2022-07-20 08:43:29.574811

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
revision = 'a1c9f3a042ad'
down_revision = u'94661459481f'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_addtofolder').prefetch_attrs():
        node.type = "workflowstep_textpage"
        node.set("alembic-{}".format(revision), "1")
        node.set("text", "WARNING: Here should be a addtofolder workflowstep, but this type got removed.")
    _core.db.session.commit()


def downgrade():
    alembic_revision = "alembic-{}".format(revision)
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_textpage').\
            filter(Node.attrs[alembic_revision] == '"1"').prefetch_attrs():
        del node.attrs[alembic_revision]
        node.attrs.pop("text", None)
        node.type = "workflowstep_addtofolder"
    _core.db.session.commit()
