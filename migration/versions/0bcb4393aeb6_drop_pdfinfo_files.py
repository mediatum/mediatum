# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop pdfinfo files

Revision ID: 0bcb4393aeb6
Revises: a9e848772043
Create Date: 2023-10-05 10:09:58.805314

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

import core as _core
import core.init as _core_init
_core_init.basic_init()
import utils.utils as _utils_utils

# revision identifiers, used by Alembic.
revision = '0bcb4393aeb6'
down_revision = u'a9e848772043'
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

    node_to_files_select = (_core.db.query(_core.NodeToFile)
            .with_entities(_core.NodeToFile.nid, _core.NodeToFile.file_id)
            .join(_core.File, _core.NodeToFile.file_id == _core.File.id)
            .filter_by(filetype='fileinfo')
        )
    node_to_files = node_to_files_select.all()
    with open(backup_dir_join("{}.fileinfo_node_to_files.json".format(revision)), "wb") as f:
        _json.dump(dict(node_to_files), f)

    node_to_files = (_core.db.query(_core.NodeToFile)
            .join(_core.File, _core.NodeToFile.file_id == _core.File.id)
            .filter_by(filetype='fileinfo')
            .all()
        )
    for node_to_file in node_to_files:
        _core.db.session.delete(node_to_file)

    _core.db.session.commit()


def downgrade():
    _core.config.initialize()

    backup_dir_join = _functools.partial(
        _os.path.join,
        _core.config.get("paths.datadir"),
        "alembic-backup",
    )
    node_to_files = backup_dir_join("{}.fileinfo_node_to_files.json".format(revision))
    if not _os.path.exists(node_to_files):
        return

    with open(node_to_files, "rb") as f:
        data = _json.load(f)
    for nid, file_id in data.iteritems():
        node_to_file = _core.NodeToFile()
        node_to_file.nid = int(nid)
        node_to_file.file_id = file_id
        _core.db.session.add(node_to_file)

    _core.db.session.commit()
