"""drop metafield message

Revision ID: e6e6c4d91968
Revises: 575d05098d4e
Create Date: 2021-03-10 06:21:25.260444

"""

# revision identifiers, used by Alembic.
revision = 'e6e6c4d91968'
down_revision = '575d05098d4e'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
import schema.schema as _schema

_q = _core.db.query

def upgrade():
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'message').prefetch_attrs():
        metafield.attrs['type'] = u'text'
    _core.db.session.commit()


def downgrade():
    pass
