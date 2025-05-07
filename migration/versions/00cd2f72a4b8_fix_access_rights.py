"""fix_access_rights

Revision ID: 00cd2f72a4b8
Revises: 94ba89894de9
Create Date: 2025-05-05 14:46:21.883709

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import os as _os

import sqlalchemy as _sqlalchemy

import core as _core
import core.init as _
_core.init.full_init()

_logg = _logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '00cd2f72a4b8'
down_revision = u'94ba89894de9'
branch_labels = None
depends_on = None


def upgrade():
    node_ids = True
    while node_ids:
        sql = _sqlalchemy.select([_sqlalchemy.column('nid')]).select_from(_sqlalchemy.func.integrity_check_inherited_access_rules().alias())
        node_ids = _core.db.session.execute(sql).fetchall()
        for node_id,  in node_ids:
            _logg.info("fixing inherited access rules for node %s", node_id)
            _core.db.query(_sqlalchemy.func.update_inherited_access_rules_for_node(node_id)).all()
    _core.db.session.commit()


def downgrade():
    pass
