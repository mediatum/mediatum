# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""remove orphan metadata

Revision ID: a5b3aec3bd5b
Revises: a003b964f915
Create Date: 2021-07-30 09:42:50.020298

"""

# revision identifiers, used by Alembic.
revision = 'a5b3aec3bd5b'
down_revision = '79cc3a51f0ac'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
import schema.schema as _schema
import core.database.postgres.node as _node


_q = _core.db.query

def upgrade():
    cids = _q(_node.t_noderelation.c.cid).filter(_node.t_noderelation.c.nid == 1)

    for ntype, nfctn in (
            # Order matters!
            # Deleting a Metadatatype would also recursively delete
            # its Fields and Masks, but would fail
            # if two fields share the same name.
            (_schema.Metafield, _core.db.session.delete),
            (_schema.Maskitem, _core.db.session.delete),
            (_schema.Mask, _schema.delete_mask),
            (_schema.Metadatatype, _schema._delete_metadatatype),
           ):
        map(nfctn, _q(ntype).filter(_core.Node.id.notin_(cids)))
        _core.db.session.commit()


def downgrade():
    pass
