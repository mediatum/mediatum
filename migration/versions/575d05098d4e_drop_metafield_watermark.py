"""drop metafield watermark

Revision ID: 575d05098d4e
Revises: 45c31b0e3274
Create Date: 2021-03-02 07:03:59.734404

"""

# revision identifiers, used by Alembic.
revision = '575d05098d4e'
down_revision = '45c31b0e3274'
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
    for metafield in _q(_schema.Metafield).filter(_schema.Metafield.a.type == 'watermark').prefetch_attrs():
        metafield.attrs['type'] = u'text'
    _core.db.session.commit()


def downgrade():
    pass
