"""fix_access_rules_inheritation

Revision ID: 04ca61e54c2d
Revises: 68c02bd743d8
Create Date: 2022-11-28 10:18:43.595639

"""


from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

# revision identifiers, used by Alembic.
revision = '04ca61e54c2d'
down_revision = u'68c02bd743d8'
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
          WITH
            RECURSIVE parent_rule_ids_nested(nid, rule_ids) AS (
                SELECT nodemapping.nid,
                (SELECT array_agg(rule_id) FROM node_to_access_rule WHERE node_to_access_rule.nid=nodemapping.nid)
                FROM  nodemapping
                WHERE nodemapping.cid = node_id
              UNION ALL
                SELECT nodemapping.nid,
                (SELECT array_agg(rule_id) FROM node_to_access_rule WHERE node_to_access_rule.nid=nodemapping.nid)
                FROM nodemapping
                JOIN parent_rule_ids_nested ON nodemapping.cid = parent_rule_ids_nested.nid
                WHERE parent_rule_ids_nested.rule_ids IS NULL
            )
          ,
            parent_rule_ids AS (
              SELECT nid,unnest(rule_ids) AS rule_id
              FROM parent_rule_ids_nested
            )
          SELECT DISTINCT
             node_id AS nid
            ,node_to_access_rule.rule_id
            ,_ruletype
            ,node_to_access_rule.invert
            ,TRUE AS inherited
            ,FALSE AS blocking
          FROM node_to_access_rule
          JOIN parent_rule_ids
            ON parent_rule_ids.nid=node_to_access_rule.nid AND parent_rule_ids.rule_id=node_to_access_rule.rule_id
          WHERE node_to_access_rule.ruletype=_ruletype;
        END;
        $f$;

        CREATE OR REPLACE FUNCTION on_node_to_access_rule_insert_delete()
            RETURNS trigger
            LANGUAGE plpgsql
            SET search_path TO mediatum
            VOLATILE
        AS $f$
        DECLARE
            c record;
            rec node_to_access_rule;
        BEGIN

        IF TG_OP = 'INSERT' THEN
            rec = NEW;
        ELSE
            rec = OLD;
        END IF;
        IF rec.ruletype IN ('read', 'data') THEN
            FOR c IN SELECT cid FROM noderelation WHERE nid = rec.nid LOOP
                -- RAISE DEBUG 'updating access rules for node %', c;
                -- ignore nodes that have their own access rules
                IF NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=c.cid AND ruletype = rec.ruletype AND inherited = false) THEN
                    DELETE FROM node_to_access_rule WHERE nid=c.cid AND inherited = true AND ruletype = rec.ruletype;
                    INSERT INTO node_to_access_rule SELECT * from _inherited_access_rules_read_type(c.cid, rec.ruletype);
                END IF;
            END LOOP;
        ELSE
            FOR c in SELECT cid FROM noderelation WHERE nid = rec.nid LOOP
                DELETE FROM node_to_access_rule WHERE nid = c.cid AND inherited = true AND ruletype = rec.ruletype;

                INSERT INTO node_to_access_rule
                SELECT * from inherited_access_rules_write(c.cid) t
                WHERE NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=t.nid AND rule_id=t.rule_id AND ruletype='write');
            END LOOP;
        END IF;
        RETURN NULL;
        END;
        $f$;

        CREATE OR REPLACE FUNCTION on_node_to_access_ruleset_delete()
            RETURNS trigger
            LANGUAGE plpgsql
            SET search_path TO mediatum
            VOLATILE
        AS $f$
        BEGIN
            DELETE FROM node_to_access_rule
            WHERE nid=OLD.nid
            AND ruletype=OLD.ruletype
            AND (nid, rule_id, ruletype, invert, false, blocking)
                NOT IN (SELECT na.nid, arr.rule_id, na.ruletype, na.invert != arr.invert, false, na.blocking OR arr.blocking
                            FROM access_ruleset_to_rule arr
                            JOIN node_to_access_ruleset na ON arr.ruleset_name=na.ruleset_name
                            WHERE na.nid=OLD.nid);

            IF OLD.ruletype IN ('read', 'data')
                AND NOT EXISTS (SELECT FROM node_to_access_ruleset WHERE nid=OLD.nid AND ruletype=OLD.ruletype)
                AND NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=OLD.nid AND ruletype=OLD.ruletype) THEN
                -- inherit from parents if no rules and rulesets are present for the node anymore
                INSERT INTO node_to_access_rule SELECT * FROM _inherited_access_rules_read_type(OLD.nid, OLD.ruletype);
            END IF;
        RETURN OLD;
        END;
        $f$;

        CREATE OR REPLACE FUNCTION on_node_to_access_ruleset_insert()
            RETURNS trigger
            LANGUAGE plpgsql
            SET search_path TO mediatum
            VOLATILE
        AS $f$
        BEGIN
            IF NEW.ruletype in ('read', 'data') THEN
                -- clear inherited rules first for read-type rules
                DELETE FROM node_to_access_rule
                WHERE nid=NEW.nid
                AND ruletype=NEW.ruletype
                AND inherited=true;
            END IF;

            INSERT INTO node_to_access_rule
            SELECT NEW.nid AS nid,
                   rule_id,
                   NEW.ruletype AS ruletype,
                   invert != NEW.invert AS invert,
                   false as inherited,
                   blocking OR NEW.blocking AS blocking
            FROM access_ruleset_to_rule
            WHERE ruleset_name=NEW.ruleset_name
            ON CONFLICT DO NOTHING;

        RETURN NEW;
        END;
        $f$;


        CREATE OR REPLACE FUNCTION recalculate_relation_subtree(root_id integer, OUT inserted integer, OUT deleted integer, OUT affected_relations integer) RETURNS record
            LANGUAGE plpgsql
            SET search_path = mediatum
            AS $f$
        DECLARE
            rel RECORD;
            ins integer;
            del integer;
        BEGIN

        deleted := 0;
        inserted := 0;
        affected_relations := 0;

        -- LOCK TABLE noderelation IN EXCLUSIVE MODE;

        -- check all connections to children of root
        FOR rel IN SELECT cid, distance FROM noderelation WHERE nid = root_id LOOP

            -- RAISE DEBUG 'DELETE FROM noderelation nr WHERE nr.cid = % AND nr.distance > %', rel.cid, rel.distance;

            -- only delete tuples belonging to paths which could go through root_id
            DELETE FROM noderelation nr
            WHERE nr.cid = rel.cid
            AND nr.distance > rel.distance
            ;
            GET DIAGNOSTICS del = ROW_COUNT;

            -- RAISE DEBUG 'INSERT INTO noderelation SELECT DISTINCT * FROM transitive_closure_for_node(%)', rel.cid;

            INSERT INTO noderelation
            SELECT DISTINCT * FROM transitive_closure_for_node(rel.cid)
            WHERE distance > rel.distance
            ;
             GET DIAGNOSTICS ins = ROW_COUNT;

            -- RAISE DEBUG 'cid % distance %, deleted %, inserted %', rel.cid, rel.distance, del, ins;

            PERFORM update_inherited_access_rules_for_node(rel.cid);

            inserted := inserted + ins;
            deleted := deleted + del;
            affected_relations := affected_relations + 1;

        END LOOP;
        END;
        $f$;

        DROP FUNCTION _update_children_inherited_rules
    """))
