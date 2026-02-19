# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""rename_citeproc_in_import-citeproc

Revision ID: 8c9d604339be
Revises: dd1677dbfaf5
Create Date: 2026-02-27 08:16:59.882183

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
import schema as _schema
import schema.mapping as _
import schema.schema as _

# revision identifiers, used by Alembic.
revision = '8c9d604339be'
down_revision = 'dd1677dbfaf5'
branch_labels = None
depends_on = None

_logg = _logging.getLogger(__name__)


def _rename_mask(schema, old_name, new_name):
    """
    Rename the schema's mask named `old_name` to `new_name`,
    and return the renamed mask.
    If `old_name` does not exist, or `new_name` alread exists,
    do and return nothing.
    """
    mask = schema.get_mask(old_name)
    if not mask:
        return
    if schema.get_mask(new_name):
        _logg.warning("%s (%s): mask '%s' (%s) not renamed, as target name '%s' already exists",
                  schema.name, schema.id, old_name, mask.id, new_name)
        return
    _logg.info("%s (%s): rename mask '%s' (%s) in '%s'", schema.name, schema.id, old_name, mask.id, new_name)
    mask.name = new_name
    return mask


def upgrade():
    for schema in _core.db.query(_schema.schema.Metadatatype):
        mask = _rename_mask(schema, 'citeproc', 'import-citeproc')
        if not mask:
            continue
        for maskitem in mask.all_maskitems:
            if 'mappingfield' in maskitem and maskitem.get("fieldtype") == "mapping":
                # The `mappingfield` must not fall out of scope and
                # become liable to Python's garbage collection before
                # its `.attrs` have been modified, so we assign it
                # to a separate variable here before changing it.
                mappingfield = _core.db.query(_schema.mapping.MappingField).get(maskitem["mappingfield"])
                mappingfield.attrs.pop("exportformat", None)
    _core.db.session.commit()


def downgrade():
    for schema in _core.db.query(_schema.schema.Metadatatype):
        _rename_mask(schema, 'import-citeproc', 'citeproc')
    _core.db.session.commit()
