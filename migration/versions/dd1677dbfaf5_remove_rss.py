# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""remove_rss

Revision ID: dd1677dbfaf5
Revises: efd25c20e5bf
Create Date: 2026-02-27 07:10:05.544114

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _
_core.init.full_init()
import core.nodecache as _
import schema as _schema
import schema.mapping as _

# revision identifiers, used by Alembic.
revision = 'dd1677dbfaf5'
down_revision = 'efd25c20e5bf'
branch_labels = None
depends_on = None

_logg = _logging.getLogger(__name__)


def upgrade():
    mappings = _core.nodecache.get_mappings_node()
    mappingtypes = mappings.attrs.pop("mappingtypes", "").split(';')
    while "rss" in mappingtypes:
        mappingtypes.remove("rss")
    if mappingtypes:
        mappings.set("mappingtypes", ';'.join(mappingtypes))
    for mapping in _core.db.query(_schema.mapping.Mapping):
        if mapping.get("mappingtype") == "rss":
            _logg.warning("%s (%s): changing mappingtype 'rss' -> 'default'", mapping.name, mapping.id)
            mapping.set("mappingtype", "default")
    _core.db.session.commit()


def downgrade():
    mappings = _core.nodecache.get_mappings_node()
    mappingtypes = mappings.get("mappingtypes", "").split(';')
    if "rss" not in mappingtypes:
        mappingtypes.append("rss")
        mappings.set("mappingtypes", ';'.join(mappingtypes))
        _core.db.session.commit()
