"""upgrade accessible_container_paths

Revision ID: 160fac8bb7dd
Revises: a32ec9c3e5c5
Create Date: 2022-01-21 13:45:32.870348

"""

# revision identifiers, used by Alembic.
revision = '160fac8bb7dd'
down_revision = 'a32ec9c3e5c5'
branch_labels = None
depends_on = None

import os as _os
import sys as _sys
import textwrap as _textwrap

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import alembic as _alembic

import core as _core
import core.init as _core_init
_core_init.full_init()


def upgrade():
    _alembic.op.execute("DROP FUNCTION IF EXISTS accessible_container_paths(int, int[], int[], inet, date)")
    _core.db.create_functions(_core.db.session)
    _core.db.session.commit()


def downgrade():
    _alembic.op.execute("DROP FUNCTION IF EXISTS accessible_container_paths(int, int[], inet, date)")
    _alembic.op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.accessible_container_paths(node_id integer, exclude_container_ids integer[] DEFAULT ARRAY[]::integer[], group_ids integer[] DEFAULT NULL::integer[], ipaddr inet DEFAULT NULL::inet, date date DEFAULT NULL::date)
         RETURNS SETOF integer[]
         LANGUAGE plpgsql
         IMMUTABLE
         SET search_path TO 'mediatum'
        AS $function$
        BEGIN
        RETURN QUERY SELECT
            (SELECT array_append(array_agg(q.nid), nm.nid)
             FROM (SELECT nid
                   FROM noderelation nr
                   WHERE nr.cid=nm.nid
                   AND has_read_access_to_node(nr.nid, group_ids, ipaddr, date)
                   AND NOT ARRAY[nr.nid] <@ exclude_container_ids
                   ORDER BY distance DESC) q) as path

            FROM nodemapping nm
            WHERE cid=node_id
            AND NOT ARRAY[nm.nid] <@ exclude_container_ids
            AND has_read_access_to_node(nm.nid, group_ids, ipaddr, date);
        END;
        $function$
    """))
