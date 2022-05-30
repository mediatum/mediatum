# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""drop fts_bak table

Revision ID: 45c31b0e3274
Revises: 5f09bbe431bb
Create Date: 2020-02-26 07:52:45.303507

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = '45c31b0e3274'
down_revision = 'b65927fda313'
branch_labels = None
depends_on = None

import textwrap as _textwrap
import alembic as _alembic


def upgrade():
    # drop table fts_bak
    _alembic.op.execute('DROP TABLE mediatum.fts_bak')

    # drop fts_id_seq
    _alembic.op.execute('DROP SEQUENCE mediatum.fts_id_seq')


def downgrade():
    # create table fts_bak
    _alembic.op.execute(_textwrap.dedent("""
        CREATE TABLE mediatum.fts_bak (
            id integer NOT NULL,
            nid integer NOT NULL,
            config text NOT NULL,
            searchtype text NOT NULL,
            tsvec tsvector
        )
    """))
    _alembic.op.execute('ALTER TABLE ONLY mediatum.fts_bak ALTER COLUMN tsvec SET STATISTICS 10000')
    _alembic.op.execute(_textwrap.dedent("""
        CREATE SEQUENCE mediatum.fts_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1
    """))
    _alembic.op.execute('ALTER SEQUENCE mediatum.fts_id_seq OWNED BY mediatum.fts_bak.id')
    _alembic.op.execute(_textwrap.dedent("""
        ALTER TABLE ONLY mediatum.fts_bak ALTER COLUMN id SET DEFAULT nextval('mediatum.fts_id_seq'::regclass)
    """))

    # create function insert_node_tsvectors to insert attrs and fulltext of one node
    _alembic.op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.insert_node_tsvectors(_id integer)
         RETURNS void
         LANGUAGE plpgsql
         SET search_path TO mediatum
        AS $function$
        DECLARE
            searchconfig regconfig;
            fulltext_autoindex_languages text[];
            attribute_autoindex_languages text[];
            _tsvec  tsvector;
            _nid    integer;
        BEGIN
            fulltext_autoindex_languages = get_fulltext_autoindex_languages();

            IF fulltext_autoindex_languages IS NOT NULL THEN
                FOREACH searchconfig IN ARRAY fulltext_autoindex_languages LOOP
                    SELECT tsvec,nid INTO _tsvec,_nid FROM fts_bak WHERE nid=_id AND searchtype='fulltext' AND config=searchconfig::text;
                    IF _tsvec IS NULL AND _nid IS NOT NULL THEN
                        DELETE FROM fts_bak WHERE nid=_id AND searchtype='fulltext' AND config=searchconfig::text;
                    END IF;
                    IF _tsvec IS NULL THEN
                        INSERT INTO fts_bak (nid, config, searchtype, tsvec)
                        SELECT id, searchconfig, 'fulltext', to_tsvector_safe(searchconfig, fulltext)
                        FROM node WHERE id=_id;
                    END IF;
                END LOOP;
            END IF;

            attribute_autoindex_languages = get_attribute_autoindex_languages();

            IF attribute_autoindex_languages IS NOT NULL THEN
                FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
                    SELECT tsvec INTO _tsvec FROM fts_bak WHERE nid=_id AND searchtype='attrs' AND config=searchconfig::text;
                    IF _tsvec IS NULL THEN
                        INSERT INTO fts_bak (nid, config, searchtype, tsvec)
                        SELECT id, searchconfig, 'attrs', jsonb_object_values_to_tsvector(searchconfig, attrs)
                        FROM node WHERE id=_id;
                    END IF;
                END LOOP;
            END IF;
        END;
        $function$
    """))

    # fill table fts_bak
    op.execute(_textwrap.dedent("""
        SELECT mediatum.insert_node_tsvectors(id) FROM node WHERE id IN
            (SELECT cid FROM noderelation WHERE nid in
                (SELECT id FROM node WHERE type = 'root'))
        AND type IN (SELECT name FROM mediatum.nodetype WHERE is_container = false)
    """))

    # create function create_fts_bak_indexes
    _alembic.op.execute(_textwrap.dedent("""
        CREATE OR REPLACE FUNCTION mediatum.create_fts_bak_indexes() RETURNS void
         LANGUAGE plpgsql
         SET search_path TO mediatum
        AS $function$
        DECLARE
            searchconfig regconfig;
            fulltext_autoindex_languages text[];
            attribute_autoindex_languages text[];

        BEGIN
            attribute_autoindex_languages = get_attribute_autoindex_languages();
            fulltext_autoindex_languages = get_fulltext_autoindex_languages();

            IF attribute_autoindex_languages IS NOT NULL THEN
                FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
                    EXECUTE 'CREATE INDEX fts_attrs_' || searchconfig
                            || ' ON fts_bak USING gin(tsvec) WHERE config = ''' || searchconfig || ''''
                            || ' AND searchtype = ''attrs''';
                END LOOP;
            END IF;

            IF fulltext_autoindex_languages IS NOT NULL THEN
                FOREACH searchconfig IN ARRAY fulltext_autoindex_languages LOOP
                    EXECUTE 'CREATE INDEX fts_fulltext_' || searchconfig
                            || ' ON fts_bak USING gin(tsvec) WHERE config = ''' || searchconfig || ''''
                            || ' AND searchtype = ''fulltext''';
                END LOOP;
            END IF;
        END;
        $function$
    """))

    # create indexes for table fts_bak
    _alembic.op.execute('SELECT mediatum.create_fts_bak_indexes()')
    _alembic.op.create_primary_key('fts_pkey', 'fts_bak', ['nid','config','searchtype'])
