"""read_write_access_fctns_without_node_table

Revision ID: bd53a7aeaae8
Revises: 0160fbf7c4ff
Create Date: 2023-06-28 07:35:29.033126

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange


# revision identifiers, used by Alembic.
revision = 'bd53a7aeaae8'
down_revision = u'0160fbf7c4ff'
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
        CREATE OR REPLACE FUNCTION mediatum._has_read_type_access_to_node(node_id integer, _ruletype text, _group_ids integer[], ipaddr inet, _date date)
         RETURNS boolean
         LANGUAGE plpgsql
         STABLE
         SET search_path TO 'mediatum'
        AS $function$
        BEGIN
        RETURN EXISTS (
            SELECT FROM node
            JOIN node_to_access_rule na on node.id=na.nid
            JOIN access_rule a on na.rule_id=a.id
            WHERE na.ruletype=_ruletype
            AND node.id = node_id
            AND na.invert != check_access_rule(a, _group_ids, ipaddr, _date));
        END;
        $function$;

        CREATE OR REPLACE FUNCTION mediatum._has_write_type_access_to_node(node_id integer, _ruletype text, _group_ids integer[], ipaddr inet, _date date)
         RETURNS boolean
         LANGUAGE plpgsql
         STABLE
         SET search_path TO 'mediatum'
        AS $function$
        BEGIN
        RETURN EXISTS (
            SELECT node.id FROM node
            JOIN node_to_access_rule na on node.id=na.nid
            JOIN access_rule a on na.rule_id=a.id
            WHERE na.ruletype=_ruletype
            AND na.blocking = false
            AND node.id = node_id
            AND na.invert != check_access_rule(a, _group_ids, ipaddr, _date)

            EXCEPT

            SELECT node.id FROM node
            JOIN node_to_access_rule na on node.id=na.nid
            JOIN access_rule a on na.rule_id=a.id
            WHERE na.ruletype=_ruletype
            AND na.blocking = true
            AND node.id = node_id
            AND NOT na.invert != check_access_rule(a, _group_ids, ipaddr, _date));

        END;
        $function$;
    """))
