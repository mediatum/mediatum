# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""htmlmemo add entermode to metatype-data

Revision ID: cac6cf00a85a
Revises: ed88eef38764
Create Date: 2024-04-23 11:33:30.442937

The entermode attribute determine Enter-Key behavior of htmlmemo fields
Options are:
enter-p: wrap each line in p-tags
enter-br: insert a <br \>
enter-div: wrap lines in div-tags

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
revision = 'cac6cf00a85a'
down_revision = u'81a3d17301ab'
branch_labels = None
depends_on = None


def upgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == "htmlmemo").prefetch_attrs():
        data = metafield.metatype_data
        data["wysiwyg_entermode"] = "p"
        metafield.metatype_data = data
    _core.db.session.commit()

def downgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == "htmlmemo").prefetch_attrs():
        data = metafield.metatype_data
        del data["wysiwyg_entermode"]
        metafield.metatype_data = data
    _core.db.session.commit()
