# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""thumb2 and presentation to thumbnail

Revision ID: 89e54f1ef82d
Revises: 52ce1ef8d73b
Create Date: 2022-03-15 09:32:53.323003

change filetype = 'presentation' and filetype = 'thumb2' to 'thumbnail'
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import functools as _functools
import json as _json
import os as _os
import sqlalchemy as _sqlalchemy
import sys as _sys
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.basic_init()
import utils.utils as _utils_utils
from core.database.postgres.file import File

# revision identifiers, used by Alembic.
revision = '89e54f1ef82d'
down_revision = u'52ce1ef8d73b'
branch_labels = None
depends_on = None


def upgrade():
    _core.config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core.config.get("paths.datadir"),
        "alembic-backup",
    )
    with _utils_utils.suppress(OSError, warn=False):
        _os.mkdir(backup_dir_join())

    file_select = _core.db.query(File).with_entities(File.id, File.filetype).filter(
            _sqlalchemy.or_(File.filetype == u'thumb2', File.filetype == u'presentation'),
        )
    if not file_select.first():
        return

    with open(backup_dir_join("{}.thumb2.presentation.json".format(revision)), "wb") as f:
        _json.dump(dict(file_select.all()), f)

    _core.db.session.query(File).filter(
        _sqlalchemy.or_(File.filetype == u'thumb2', File.filetype == u'presentation'),
    ).update({File.filetype: "thumbnail"}, synchronize_session=False)

    _core.db.session.commit()


def downgrade():
    _core.config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core.config.get("paths.datadir"),
        "alembic-backup",
    )
    thumb2_files = backup_dir_join("{}.thumb2.presentation.json".format(revision))
    if not _os.path.exists(thumb2_files):
        return

    with open(thumb2_files, "rb") as f:
        data = _json.load(f)
    # _core.q(File).get(fileid).filetype = filetype is very slow
    for fileid, filetype in data.iteritems():
        _core.db.session.query(File).filter(File.id == int(fileid)).update(
            {File.filetype: filetype},
            synchronize_session=False,
        )

    _core.db.session.commit()
