"""set workflowstep settings in wfs upload

Revision ID: a9e848772043
Revises: b0dfcab84653
Create Date: 2023-09-20 08:37:41.515218

"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import utils.utils as _utils_utils
import core as _core
import core.init as _core_init
_core_init.full_init()

import workflow.upload as _upload

# revision identifiers, used by Alembic.
revision = 'a9e848772043'
down_revision = u'b0dfcab84653'
branch_labels = None
depends_on = None

_valid_fileextensions = frozenset((
    "bmp",
    "gif",
    "jpeg",
    "jpg",
    "mp3",
    "mp4",
    "pdf",
    "png",
    "svg",
    "tif",
    "tiff",
))

_mimetypes = frozenset(_utils_utils.getMimeType("_.{}".format(m))[0] for m in _valid_fileextensions)

def upgrade():
    for workflowstep in _core.db.query(_upload.WorkflowStep_Upload).prefetch_attrs():
        workflowstep.settings = dict(mimetypes = tuple(_mimetypes))
    _core.db.session.commit()

def downgrade():
    for workflowstep in _core.db.query(_upload.WorkflowStep_Upload).prefetch_attrs():
        workflowstep.settings = None
    _core.db.session.commit()
