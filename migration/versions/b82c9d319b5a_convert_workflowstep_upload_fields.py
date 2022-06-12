# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""convert_workflowstep_upload_fields

Revision ID: b82c9d319b5a
Revises: 975b96703a01
Create Date: 2022-10-06 07:05:11.976230

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
from core.database.postgres.node import Node

# revision identifiers, used by Alembic.
revision = 'b82c9d319b5a'
down_revision = u'975b96703a01'
branch_labels = None
depends_on = None

_q = _core.db.query

def upgrade():
    for wfstep in ('addformpage', 'metafield2metadata', 'hierarchicalchoice2metafield', 'updateattributesfixed'):
        suffix = 'pdfform' if wfstep == 'addformpage' else 'fileatt'
        for node in _core.db.query(Node).filter(Node.type == 'workflowstep_{}'.format(wfstep)).prefetch_attrs():
            for f in node.files:
                try:
                    if f.filetype != 'metafield-upload.upload_{}'.format(suffix):
                        raise OSError  # see below
                    _os.path.getmtime(f.abspath)
                except OSError:
                    node.files.remove(f)
                    continue
            files = sorted(node.files, key=lambda f:_os.path.getmtime(f.abspath))
            if files:
                files.pop().filetype = "wfstep-{}".format(wfstep)
            for f in files:
                node.files.remove(f)
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_deletefile').prefetch_attrs():
        types = set(node.get("filetype", "").split(";"))
        if "metafield-upload.upload_pdfform" in types:
            types.add("wfstep-addformpage")
        types.discard("metafield-upload.upload_pdfform")
        node.set("filetype", ";".join(types))
    _core.db.session.commit()


def downgrade():
    for wfstep in ('addformpage', 'metafield2metadata', 'hierarchicalchoice2metafield', 'updateattributesfixed'):
        suffix = 'pdfform' if wfstep == 'addformpage' else 'fileatt'
        for node in _core.db.query(Node).filter(Node.type == 'workflowstep_{}'.format(wfstep)).prefetch_attrs():
            for f in node.files:
                f.filetype = 'metafield-upload.upload_{}'.format(suffix)
    for node in _core.db.query(Node).filter(Node.type == 'workflowstep_deletefile').prefetch_attrs():
        types = set(node.get("filetype", "").split(";"))
        if "wfstep-addformpage" in types:
            types.add("metafield-upload.upload_pdfform")
        types.discard("wfstep-addformpage")
        node.set("filetype", ";".join(types))
    _core.db.session.commit()
