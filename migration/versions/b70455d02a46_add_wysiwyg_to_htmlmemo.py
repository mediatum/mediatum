# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""add_wysiwyg_to_htmlmemo

Revision ID: b70455d02a46
Revises: b4f67e88ce51
Create Date: 2022-04-22 06:07:01.576940

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
import schema.schema as _schema


# revision identifiers, used by Alembic.
revision = 'b70455d02a46'
down_revision = u'b4f67e88ce51'
branch_labels = None
depends_on = None

_q = _core.db.query


def upgrade():
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'htmlmemo').prefetch_attrs():
        data = metafield.metatype_data
        data["wysiwyg"] = True
        metafield.metatype_data = data
    _core.db.session.commit()


def downgrade():
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'htmlmemo').prefetch_attrs():
        data = metafield.metatype_data
        del data["wysiwyg"]
        metafield.metatype_data = data
    _core.db.session.commit()
