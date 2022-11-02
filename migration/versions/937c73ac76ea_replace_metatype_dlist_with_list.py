# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""replace_metatype_dlist_with_list

Revision ID: 937c73ac76ea
Revises: a0f87284aaa4
Create Date: 2022-05-19 05:58:40.489000

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import sys as _sys

import json as _json

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
import core.nodecache as _nodecache
_core_init.full_init()
import schema.schema as _schema


# revision identifiers, used by Alembic.
revision = '937c73ac76ea'
down_revision = u'a0f87284aaa4'
branch_labels = None
depends_on = None

_q = _core.db.query


def upgrade():
    for metadatatype in _nodecache.get_metadatatypes_node().children:
        for metafield in metadatatype.children.filter(_schema.Metafield.a.type=='dlist'):
            listelements = _nodecache.get_root_node().all_children_by_query(
                _q(_core.Node.a[metafield.name])
                .filter(_core.Node.schema==metadatatype.name)
               ).all()
            listelements = set(elem for elem, in listelements)
            listelements.discard(None)
            metafield.setFieldtype("list")
            metafield.metatype_data = dict(listelements=tuple(listelements), multiple=False)
    _core.db.session.commit()


def downgrade():
    pass
