"""replace directory attachment by files

Revision ID: 9bc074be7a67
Revises: 8251e44a3fea
Create Date: 2024-12-19 13:08:52.470604

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import os as _os

import core as _core
import core.init as _
_core.init.full_init()
import core.config as _
import core.database.postgres.file as _
import core.database.postgres.node as _
import utils as _utils
import utils.utils as _


_logg = _logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '9bc074be7a67'
down_revision = u'8251e44a3fea'
branch_labels = None
depends_on = None


def upgrade():
    basedir = _core.config.get("paths.datadir")
    query = _core.db.query(_core.database.postgres.file.NodeToFile).with_entities(
        _core.database.postgres.file.NodeToFile.nid.label("nid"),
        _core.database.postgres.file.NodeToFile.file_id.label("fid"),
        _core.database.postgres.file.File.path.label("path"),
        ).join(
        _core.database.postgres.file.File,
        _core.database.postgres.file.NodeToFile.file_id == _core.database.postgres.file.File.id,
        ).filter_by(mimetype='inode/directory').join(
        _core.database.postgres.node.Node,
        _core.database.postgres.file.NodeToFile.nid == _core.database.postgres.node.Node.id,
        )
    for file in query.all():
        fullpath = _os.path.join(basedir, file.path)
        node = _core.db.query(_core.database.postgres.node.Node).get(file.nid)
        count = 0
        for root, _, filenames in _os.walk(fullpath):
            count += len(filenames)
            node.files.extend(_core.database.postgres.file.File(
                _os.path.relpath(_os.path.join(root, filename), basedir),
                u"attachment",
                _utils.utils.getMimeType(filename.lower())[0],
                ) for filename in filenames)
        node.files.remove(_core.db.query(_core.database.postgres.file.File).get(file.fid))
        _logg.info("node %s, attachment directory %s ('%s'): replaced with %s attachment file(s)",
                   file.nid, file.fid, file.path, count)
        _core.db.session.commit()


def downgrade():
    pass
