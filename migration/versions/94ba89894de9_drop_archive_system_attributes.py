"""drop_archive_system_attributes

Revision ID: 94ba89894de9
Revises: 9bc074be7a67
Create Date: 2025-03-31 13:46:12.584382

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import sqlalchemy as _sqlalchemy

import core as _core
import core.init as _
_core.init.full_init()
import contenttypes as _contenttypes
import core.database.postgres.node as _

# revision identifiers, used by Alembic.
revision = '94ba89894de9'
down_revision = u'9bc074be7a67'
branch_labels = None
depends_on = None


def upgrade():
    for node in (_core.db.query(_contenttypes.data.Data)
                 .filter(_sqlalchemy.or_(
                     _contenttypes.data.Data.system_attrs['archive_path'].isnot(None),
                     _contenttypes.data.Data.system_attrs['archive_type'].isnot(None),
                    ))
                 .prefetch_system_attrs()):
        node.system_attrs.pop("archive_path", None)
        node.system_attrs.pop("archive_type", None)
    _core.db.session.commit()


def downgrade():
    pass
