# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""replace_metatype_memo_with_htmlmemo

Revision ID: a0f87284aaa4
Revises: b70455d02a46
Create Date: 2022-04-22 07:23:07.239672

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
revision = 'a0f87284aaa4'
down_revision = u'b70455d02a46'
branch_labels = None
depends_on = None

_q = _core.db.query


def upgrade():
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'memo').prefetch_attrs():
        data = metafield.metatype_data
        metafield.setFieldtype("htmlmemo")
        data["wysiwyg"] = False
        metafield.metatype_data = data
    _core.db.session.commit()


def downgrade():
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'htmlmemo').prefetch_attrs():
        data = metafield.metatype_data
        if data['wysiwyg']:
            continue
        metafield.set('type', 'memo')
        del data["wysiwyg"]
        metafield.metatype_data = data
    _core.db.session.commit()
