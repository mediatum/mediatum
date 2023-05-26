"""fileversion filetype to thumbnail

Revision ID: 0160fbf7c4ff
Revises: 92392b1c2faa
Create Date: 2023-05-26 07:38:41.667154

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
import sys as _sys
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

from sqlalchemy.sql import expression as _sqlalchemy_sql_expression
from sqlalchemy_continuum import utils as _sqlalchemy_continuum_utils

import core as _core
import core.init as _core_init
_core_init.full_init()
import utils.utils as _utils_utils
from core.database.postgres import file as _postgres_file

# revision identifiers, used by Alembic.
revision = '0160fbf7c4ff'
down_revision = '92392b1c2faa'
branch_labels = None
depends_on = None

FileVersion = _sqlalchemy_continuum_utils.version_class(_postgres_file.File)

def upgrade():
    _core.config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core.config.get("paths.datadir"),
        "alembic-backup",
    )
    with _utils_utils.suppress(OSError, warn=False):
        _os.mkdir(backup_dir_join())

    fileversion_select = _core.db.query(FileVersion).with_entities(FileVersion.id, FileVersion.filetype).filter(
            _sqlalchemy_sql_expression.or_(FileVersion.filetype == u'thumb2', FileVersion.filetype == u'presentation'),
        )
    if not fileversion_select.first():
        return

    with open(backup_dir_join("{}.fileversion.filetype.to.thumbnail.json".format(revision)), "wb") as f:
        _json.dump(dict(fileversion_select.all()), f)

    _core.db.session.query(FileVersion).filter(
        _sqlalchemy_sql_expression.or_(FileVersion.filetype == u'thumb2', FileVersion.filetype == u'presentation'),
    ).update({FileVersion.filetype: "thumbnail"}, synchronize_session=False)

    _core.db.session.commit()


def downgrade():
    _core.config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core.config.get("paths.datadir"),
        "alembic-backup",
    )
    thumb2_files = backup_dir_join("{}.fileversion.filetype.to.thumbnail.json".format(revision))
    if not _os.path.exists(thumb2_files):
        return

    with open(thumb2_files, "rb") as f:
        data = _json.load(f)
    for fileid, filetype in data.iteritems():
        _core.db.session.query(FileVersion).filter(FileVersion.id == int(fileid)).update(
            {FileVersion.filetype: filetype},
            synchronize_session=False,
        )

    _core.db.session.commit()
