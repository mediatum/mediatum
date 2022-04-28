# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""replace regexp_split_to_array by string_to_array

Revision ID: 5f09bbe431bb
Revises: 6cd40ed911a7
Create Date: 2019-12-06 08:26:38.015226

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = '5f09bbe431bb'
down_revision = '299e62976649'
branch_labels = None
depends_on = None

import textwrap as _textwrap
from alembic import op
import sqlalchemy as sa


def upgrade():
    # replace regexp_split_to_array by fast string_to_array
    op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.get_list_values_for_nodes_with_schema(schema_ text, attr text)
         RETURNS SETOF text
         LANGUAGE plpgsql
         STABLE
         SET search_path TO mediatum
        AS $function$
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
        $function$
    """));

    op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.count_list_values_for_all_content_children(parent_id integer, attr text)
         RETURNS SETOF value_and_count
         LANGUAGE plpgsql
         STABLE
         SET search_path TO mediatum
        AS $function$
        DECLARE
        BEGIN
            RETURN QUERY SELECT val, count(val)
            FROM (SELECT trim(unnest(string_to_array(attrs->>attr, ';'))) AS val
                    FROM node
                    JOIN noderelation nr on node.id=nr.cid
                    WHERE nr.nid=parent_id
                    AND node.type IN (SELECT name FROM nodetype WHERE is_container=false)) q
            WHERE val IS NOT NULL
            AND val != ''
            GROUP BY val
            ORDER BY val;
        END;
        $function$
    """));


def downgrade():
    op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.get_list_values_for_nodes_with_schema(schema_ text, attr text)
         RETURNS SETOF text
         LANGUAGE plpgsql
         STABLE
         SET search_path TO mediatum
        AS $function$
        DECLARE
        BEGIN
            RETURN QUERY SELECT DISTINCT val
            FROM (SELECT trim(unnest(regexp_split_to_array(attrs->>attr, ';'))) AS val
                    FROM node
                    WHERE node.schema=schema_) q
            WHERE val IS NOT NULL
            AND val != ''
            ORDER BY val;
        END;
        $function$
    """));

    op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.count_list_values_for_all_content_children(parent_id integer, attr text)
         RETURNS SETOF value_and_count
         LANGUAGE plpgsql
         STABLE
         SET search_path TO mediatum
        AS $function$
        DECLARE
        BEGIN
            RETURN QUERY SELECT val, count(val)
            FROM (SELECT trim(unnest(regexp_split_to_array(attrs->>attr, ';'))) AS val
                    FROM node
                    JOIN noderelation nr on node.id=nr.cid
                    WHERE nr.nid=parent_id
                    AND node.type IN (SELECT name FROM nodetype WHERE is_container=false)) q
            WHERE val IS NOT NULL
            AND val != ''
            GROUP BY val
            ORDER BY val;
        END;
        $function$
    """));
