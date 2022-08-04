# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop_metafield_upload

Revision ID: 65da41555319
Revises: b82c9d319b5a
Create Date: 2022-10-11 06:15:31.479671

"""

from __future__ import division
from __future__ import print_function

# revision identifiers, used by Alembic.
revision = '65da41555319'
down_revision = u'b82c9d319b5a'
branch_labels = None
depends_on = None

import collections as _collections
import functools as _functools
import json as _json
import logging as _logging
import os as _os
import sys as _sys

import sqlalchemy as _sqlalchemy

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
import core.config as _core_config
import contenttypes as _contenttypes
import schema.schema as _schema
import utils.utils as _utils
from core.database.postgres.file import File
from core.database.postgres.node import Node


_logg = _logging.getLogger(__name__)

def upgrade():
    backup_dir_join = _functools.partial(
        _os.path.join,
        _core_config.get("paths.datadir"),
        "alembic-backup",
    )
    with _utils.suppress(OSError, warn=False):
        _os.mkdir(backup_dir_join())

    metafields = dict()
    for metadataschema in _core.db.query(_schema.Metadatatype):
        for metadatafield in metadataschema.children.filter(
                _sqlalchemy.and_(Node.type=='metafield',
                Node.attrs["type"].astext=="upload"),
            ).prefetch_attrs():
            nodes = _collections.defaultdict(dict)
            for node in _core.db.query(_contenttypes.data.Content).filter(Node.schema==metadataschema.name):
                filenames = list()
                for f in node.files:
                    if f.filetype != "metafield-upload.{}".format(metadatafield.name):
                        continue
                    nodes[str(node.id)][str(f.id)] = f.mimetype
                    filenames.append(f.abspath)
                    node.files.remove(f)
                if filenames:
                    node.attrs[metadatafield.name] = _json.dumps(filenames)
                del filenames
            metadatafield.attrs['type'] = "text"
            metafields[str(metadatafield.id)] = dict(name=metadatafield.name, nodes=nodes)
    with open(backup_dir_join("{}.drop-metafield-upload.json".format(revision)), "wb") as f:
        _json.dump(metafields, f)
    _core.db.session.commit()


def downgrade():
    drop_metafield_upload = _os.path.join(
        _core_config.get("paths.datadir"),
        "alembic-backup",
        "{}.drop-metafield-upload.json".format(revision),
    )
    if not _os.path.exists(drop_metafield_upload):
        return

    with open(drop_metafield_upload, "rb") as f:
        metafields = _json.load(f)

    for id_, data in metafields.iteritems():
        metafield = _core.db.query(_schema.Metafield).get(int(id_))
        if not metafield:
            _logg.warning("metafield with id = %s not found", id_)
            continue
        if metafield.name != data["name"]:
            _logg.warning("metafield.name = %s != expected name %s (id=%s)", metafield.name, data["name"], id_)
            continue
        if metafield.attrs['type'] != 'text':
            _logg.warning("type of metafield %s (id=%s): %s  is not of type text ",
                    data["name"], id_, metafield.attrs['type'])
            continue
        metafield.attrs['type'] = 'upload'
        for nid, files in data["nodes"].iteritems():
            node = _core.db.query(Node).get(int(nid))
            if not node:
                _logg.warning("node with id = %s not found", nid)
                continue
            if not node.get(data["name"]):
                _logg.warning("node (id=%s) has no attribute %s", nid, data["name"])
                continue
            file_count = 0
            for fid, mimetype in files.iteritems():
                file = _core.db.query(File).get(int(fid))
                if not file:
                    _logg.warning("file with id %s not found", fid)
                    continue
                if file.mimetype != mimetype:
                    _logg.warning("mimetype of file %s: %s != expected mimetype %s",
                                  fid, file.mimetype, mimetype)
                    continue
                node.files.append(file)
                file_count += 1
            node.attrs[metafield.name] = str(file_count)
    _core.db.session.commit()
