# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""add static to image path in valuelist attribute

Revision ID: 5a0e0e56cf66
Revises: 68c02bd743d8
Create Date: 2022-09-22 09:50:49.734135

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import core as _core
import core.init as _core_init
_core_init.basic_init()
from schema import schema as _schema_schema

# revision identifiers, used by Alembic.
revision = '5a0e0e56cf66'
down_revision = u'937c73ac76ea'
branch_labels = None
depends_on = None


def _replace_url_valuelist_url(oldnew):
    for metafield in _core.db.query(_schema_schema.Metafield).filter(
            _schema_schema.Metafield.a.type == "url",
        ).prefetch_attrs():
        data = metafield.metatype_data
        data["icon"] = oldnew.get(data["icon"], data["icon"])
        metafield.metatype_data = data

    _core.db.session.commit()


def upgrade():
    _replace_url_valuelist_url({"/img/extlink.png": "/static/img/extlink.png", "/img/email.png": "/static/img/email.png"})


def downgrade():
    _replace_url_valuelist_url({"/static/img/extlink.png": "/img/extlink.png", "/static/img/email.png": "/img/email.png"})
