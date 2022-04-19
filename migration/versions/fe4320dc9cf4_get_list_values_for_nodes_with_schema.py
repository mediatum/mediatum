# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""drop get_list_values_for_nodes_with_schema

Revision ID: fe4320dc9cf4
Revises: 3b473e771f5c
Create Date: 2022-04-27 12:15:48.390803

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import sys as _sys
import textwrap as _textwrap

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.basic_init()

# revision identifiers, used by Alembic.
revision = 'fe4320dc9cf4'
down_revision = '3b473e771f5c'
branch_labels = None
depends_on = None


def upgrade():
    _core.db.session.execute("DROP FUNCTION IF EXISTS get_list_values_for_nodes_with_schema(schema_ text, attr text)")
    _core.db.session.commit()


def downgrade():
    _core.db.session.execute("DROP FUNCTION IF EXISTS get_list_values_for_nodes_with_schema(schema_ text, attr text)")
    _core.db.session.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION get_list_values_for_nodes_with_schema(schema_ text, attr text) RETURNS setof text
            LANGUAGE plpgsql
            STABLE
            SET search_path TO 'mediatum'
            AS $f$
        DECLARE
        BEGIN
            RETURN QUERY SELECT DISTINCT val
            FROM (SELECT trim(unnest(string_to_array(attrs->>attr, ';'))) AS val
                    FROM node
                    WHERE node.schema=schema_) q
            WHERE val IS NOT NULL
            AND val != ''
            ORDER BY val;
        END;
        $f$;
    """))
    _core.db.session.commit()
