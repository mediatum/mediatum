# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""remove_z3950_legacy

Revision ID: 80a73dce96c8
Revises: 5d14da6ddfb1
Create Date: 2026-02-27 06:11:57.363146

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
revision = '80a73dce96c8'
down_revision = u'5d14da6ddfb1'
branch_labels = None
depends_on = None

_logg = _logging.getLogger(__name__)


def upgrade():
    mappings = _core.nodecache.get_mappings_node()
    mappingtypes = mappings.attrs.pop("mappingtypes", "").split(';')
    while "z3950" in mappingtypes:
        mappingtypes.remove("z3950")
    if mappingtypes:
        mappings.set("mappingtypes", ';'.join(mappingtypes))
    for mapping in _core.db.query(_schema.mapping.Mapping):
        if mapping.get("mappingtype") == "z3950":
            _logg.warning("%s (%s): changing mappingtype 'z3950' -> 'default'", mapping.name, mapping.id)
            mapping.set("mappingtype", "default")
    _core.db.session.commit()


def downgrade():
    mappings = _core.nodecache.get_mappings_node()
    mappingtypes = mappings.get("mappingtypes", "").split(';')
    if "z3950" not in mappingtypes:
        mappingtypes.append("z3950")
        mappings.set("mappingtypes", ';'.join(mappingtypes))
        _core.db.session.commit()
