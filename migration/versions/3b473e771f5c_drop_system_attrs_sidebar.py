# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop system_attrs sidebar

Revision ID: 3b473e771f5c
Revises: 160fac8bb7dd
Create Date: 2022-03-07 12:40:05.966646

drop node.system_attrs['sidebar'], node.system_attrs['sidebar_html'], and node.attrs['sidebartext']
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
import core.init as _core_init
_core_init.basic_init()

# revision identifiers, used by Alembic.
revision = '3b473e771f5c'
down_revision = '160fac8bb7dd'
branch_labels = None
depends_on = None


def upgrade():
    for node in _core.db.query(_core.Node).filter(_core.Node.system_attrs['sidebar'] != None).all():
        node.system_attrs.pop("sidebar")
    for node in _core.db.query(_core.Node).filter(_core.Node.system_attrs['sidebar_html'] != None).all():
        node.system_attrs.pop("sidebar_html")
    for node in _core.db.query(_core.Node).filter(_core.Node.attrs['sidebartext'] != None).all():
        node.attrs.pop("sidebartext")
    _core.db.session.commit()


def downgrade():
    pass
