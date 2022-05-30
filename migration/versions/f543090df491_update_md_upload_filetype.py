# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""update md_upload filetype

Revision ID: f543090df491
Revises: 808401bae40a
Create Date: 2021-01-14 08:32:52.340976

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = 'f543090df491'
down_revision = '808401bae40a'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys
import json as _json
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))
import functools as _functools
import sqlalchemy as _sqlalchemy
import alembic as _alembic

import core.config as _core_config
import utils.utils as _utils_utils


def upgrade():
    connection = _alembic.op.get_bind()
    paths = dict(
        path1="%m_upload_upload_fileatt%",
        path2="%m_upload_upload_pdfform%",
        path3="%m_upload_captions%",
    )
    file_select = """
        SELECT id, filetype FROM mediatum.file WHERE (path LIKE :path1 OR path LIKE :path2 OR path LIKE :path3)
        AND (filetype LIKE 'u_%' OR filetype='pdf_form')
    """

    if not connection.execute(_sqlalchemy.text("SELECT EXISTS({})".format(file_select)).bindparams(**paths)).fetchone()[0]:
        return

    _core_config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core_config.get("paths.datadir"),
        "alembic-backup",
    )
    with _utils_utils.suppress(OSError, warn=False):
        _os.mkdir(backup_dir_join())

    results = connection.execute(_sqlalchemy.text(file_select).bindparams(**paths)).fetchall()

    with open(backup_dir_join("{}.md_upload_filetype.json".format(revision)), "wb") as f:
        _json.dump(dict(results), f)

    for path in paths.itervalues():
        new_filetype = path.replace("%m_upload_", "metafield-upload.").replace("%", "")
        connection.execute(
            _sqlalchemy.text("""
                UPDATE mediatum.file SET filetype=:new_filetype
                WHERE (path LIKE :path) AND (filetype LIKE 'u_%' OR filetype='pdf_form')
            """,
            ).bindparams(path=path, new_filetype=new_filetype),
        )


def downgrade():
    connection = _alembic.op.get_bind()
    _core_config.initialize()

    md_upload_filetype = _os.path.join(
        _core_config.get("paths.datadir"),
        "alembic-backup",
        "{}.md_upload_filetype.json".format(revision),
    )
    if not _os.path.exists(md_upload_filetype):
        return

    with open(md_upload_filetype, "rb") as f:
        data = _json.load(f)
    for file_id, filetype in data.iteritems():
        connection.execute(
            _sqlalchemy.text(
                "UPDATE mediatum.file SET filetype=:filetype WHERE id=:file_id;",
            ).bindparams(filetype=filetype, file_id=file_id),
        )
