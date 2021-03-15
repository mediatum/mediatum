"""remove files uploaded by addpic2pdf

Revision ID: 808401bae40a
Revises: e6e6c4d91968
Create Date: 2021-01-13 09:09:34.286050

"""

# revision identifiers, used by Alembic.
from __future__ import division

revision = '808401bae40a'
down_revision = 'e6e6c4d91968'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys
import json as _json
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))
import functools as _functools
import alembic as _alembic
import sqlalchemy as _sqlalchemy

import core.config as _core_config
import utils.utils as _utils_utils


_file_columns = (
    "id",
    "path",
    "filetype",
    "mimetype",
    "sha512",
    "sha512_checked_at",
    "sha512_created_at",
    "sha512_ok",
    "size",
)


def upgrade():
    connection = _alembic.op.get_bind()

    file_select = """
            SELECT {} FROM mediatum.file
            WHERE path LIKE '%addpic2pdf%'
            OR path LIKE '%m_upload_logoupload%'
        """.format(", ".join(_file_columns))

    if not connection.execute(_sqlalchemy.text("SELECT EXISTS({});".format(file_select))).fetchone()[0]:
        return

    _core_config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core_config.get("paths.datadir"),
        "alembic-backup",
    )
    with _utils_utils.suppress(OSError, warn=False):
        _os.mkdir(backup_dir_join())

    results = connection.execute(_sqlalchemy.text(file_select)).fetchall()
    with open(backup_dir_join("{}.addpic2pdf_files.json".format(revision)), "wb") as f:
        _json.dump(dict((row[0], dict(zip(_file_columns,row[1:]))) for row in results), f)

    file_select = "SELECT id FROM mediatum.file WHERE path LIKE '%addpic2pdf%' OR path LIKE '%m_upload_logoupload%'"
    results = connection.execute(
        _sqlalchemy.text("SELECT * FROM mediatum.node_to_file WHERE file_id IN ({})".format(file_select))
    ).fetchall()
    with open(backup_dir_join("{}.addpic2pdf_node_to_files.json".format(revision)), "wb") as f:
        _json.dump(dict(results), f)

    connection.execute(_sqlalchemy.text("DELETE FROM mediatum.node_to_file WHERE file_id IN ({})".format(file_select)))
    connection.execute(
        _sqlalchemy.text("DELETE FROM mediatum.file WHERE path LIKE '%addpic2pdf%' OR path LIKE '%m_upload_logoupload%'"),
    )


def downgrade():
    _core_config.initialize()
    connection = _alembic.op.get_bind()

    backup_dir_join = _functools.partial(
        _os.path.join,
        _core_config.get("paths.datadir"),
        "alembic-backup",
    )
    addpic2pdf_files = backup_dir_join("{}.addpic2pdf_files.json".format(revision))
    if not _os.path.exists(addpic2pdf_files):
        return
    addpic2pdf_node_to_files = backup_dir_join("{}.addpic2pdf_node_to_files.json".format(revision))
    if not _os.path.exists(addpic2pdf_node_to_files):
        return

    with open(addpic2pdf_files, "rb") as f:
        data = _json.load(f)
    for id, column_values in data.iteritems():
        column_values["id"] = id
        connection.execute(
            _sqlalchemy.text(
                "INSERT INTO mediatum.file({}) VALUES(:{})".format(", ".join(_file_columns), ", :".join(_file_columns)),
            ).bindparams(**column_values),
        )

    with open(addpic2pdf_node_to_files, "rb") as f:
        data = _json.load(f)
    for nid, file_id in data.iteritems():
        connection.execute(
            _sqlalchemy.text(
                "INSERT INTO mediatum.node_to_file(nid, file_id) VALUES(:nid, :file_id)",
            ).bindparams(nid=int(nid), file_id=file_id),
        )
