# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""remove_zoom_files

Revision ID: 68c02bd743d8
Revises: 89e54f1ef82d
Create Date: 2022-04-14 12:10:11.822029

Drop file entries where filetype = 'zoom' in node_to_file table
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
from core.database.postgres.file import File
from core.database.postgres.file import NodeToFile

# revision identifiers, used by Alembic.
revision = '68c02bd743d8'
down_revision = u'89e54f1ef82d'
branch_labels = None
depends_on = None


def upgrade():
    node_to_files_select = _core.db.query(NodeToFile).with_entities(
            NodeToFile.nid, NodeToFile.file_id,
        ).join(File, NodeToFile.file_id == File.id).filter_by(filetype='zoom')
    if not node_to_files_select.first():
        return

    _core.config.initialize()
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core.config.get("paths.datadir"),
        "alembic-backup",
    )
    with _utils_utils.suppress(OSError, warn=False):
        _os.mkdir(backup_dir_join())

    node_to_files = node_to_files_select.all()
    with open(backup_dir_join("{}.zoom_node_to_files.json".format(revision)), "wb") as f:
        _json.dump(dict(node_to_files), f)

    node_to_files = _core.db.query(NodeToFile).join(File, NodeToFile.file_id == File.id).filter_by(filetype='zoom').all()
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
    node_to_files = backup_dir_join("{}.zoom_node_to_files.json".format(revision))
    if not _os.path.exists(node_to_files):
        return

    with open(node_to_files, "rb") as f:
        data = _json.load(f)
    for nid, file_id in data.iteritems():
        node_to_file = NodeToFile()
        node_to_file.nid = int(nid)
        node_to_file.file_id = file_id
        _core.db.session.add(node_to_file)

    _core.db.session.commit()
