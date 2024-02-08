"""change static icon path in metatype data for SVG

Revision ID: 8251e44a3fea
Revises: cac6cf00a85a
Create Date: 2024-12-10 10:23:04.838613

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
import core.init as _
_core.init.basic_init()
import schema as _schema
import schema.schema as _

# revision identifiers, used by Alembic.
revision = '8251e44a3fea'
down_revision = u'cac6cf00a85a'
branch_labels = None
depends_on = None


def _replace_url_valuelist_url(oldnew):
    for metafield in (_core.db.query(_schema.schema.Metafield)
        .filter(_schema.schema.Metafield.a.type == "url")
        .prefetch_attrs()
       ):
        data = metafield.metatype_data
        data["icon"] = oldnew.get(data["icon"], data["icon"])
        metafield.metatype_data = data
    _core.db.session.commit()

def upgrade():
    _replace_url_valuelist_url({
        "/static/img/extlink.png": "/static/img/extlink.svg",
        "/static/img/email.png": "/static/img/email.svg",
       })

def downgrade():
    _replace_url_valuelist_url({
        "/static/img/extlink.svg": "/static/img/extlink.png",
        "/static/img/email.svg": "/static/img/email.png",
       })
