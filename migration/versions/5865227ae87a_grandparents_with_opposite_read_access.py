"""grandparents_with_opposite_read_access

Revision ID: 5865227ae87a
Revises: fe4320dc9cf4
Create Date: 2022-02-11 05:33:37.949088

"""


from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange


# revision identifiers, used by Alembic.
revision = '5865227ae87a'
down_revision = 'fe4320dc9cf4'
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
    _core.db.create_functions(_core.db.session)
    _core.db.session.commit()


def downgrade():
    _alembic.op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION _inherited_access_rules_read_type(node_id integer, _ruletype text)
            RETURNS SETOF node_to_access_rule
            LANGUAGE plpgsql
            SET search_path TO mediatum
            STABLE
        AS $f$
        BEGIN
        IF EXISTS (SELECT FROM node_to_access_rule WHERE nid=node_id AND ruletype=_ruletype AND inherited = false) THEN
            RETURN;
        END IF;

        RETURN QUERY
            SELECT DISTINCT node_id AS nid, rule_id, _ruletype,
              (SELECT invert
               FROM node_to_access_rule na
               WHERE na.nid=q.nid
                 AND na.rule_id=q.rule_id
                AND na.ruletype=_ruletype) as inverted,
                TRUE AS inherited, FALSE AS blocking
            FROM (WITH RECURSIVE ra(nid, rule_ids) AS
                    (SELECT nm.nid,
                       (SELECT array_agg(rule_id) AS rule_ids
                        FROM node_to_access_rule na
                        WHERE nid=nm.nid
                          AND na.ruletype=_ruletype)
                     FROM nodemapping nm
                     WHERE nm.cid = node_id
                     UNION ALL SELECT nm.nid,
                       (SELECT array_agg(rule_id) AS rule_ids
                        FROM node_to_access_rule na
                        WHERE nid=nm.nid
                          AND na.ruletype=_ruletype)
                     FROM nodemapping nm,
                                      ra
                     WHERE nm.cid = ra.nid
                       AND ra.rule_ids IS NULL)
                  SELECT DISTINCT nid,
                                  unnest(rule_ids) AS rule_id
                  FROM ra) q;
        END;
        $f$
    """))
