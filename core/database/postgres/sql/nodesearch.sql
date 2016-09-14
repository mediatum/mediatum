CREATE OR REPLACE FUNCTION get_fulltext_autoindex_languages() RETURNS text[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    fulltext_autoindex_languages text[];
BEGIN
    SELECT array_agg(v)
    FROM (SELECT jsonb_array_elements_text(value) v FROM setting WHERE key = 'search.fulltext_autoindex_languages') q
    INTO fulltext_autoindex_languages;
RETURN fulltext_autoindex_languages;
END;
$$;


CREATE OR REPLACE FUNCTION get_attribute_autoindex_languages() RETURNS text[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    attribute_autoindex_languages text[];
BEGIN
    SELECT array_agg(v)
    FROM (SELECT jsonb_array_elements_text(value) v FROM setting WHERE key = 'search.attribute_autoindex_languages') q
    INTO attribute_autoindex_languages;
RETURN attribute_autoindex_languages;
END;
$$;


CREATE OR REPLACE FUNCTION insert_node_tsvectors() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig regconfig;
    fulltext_autoindex_languages text[];
    attribute_autoindex_languages text[];
BEGIN
    fulltext_autoindex_languages = get_fulltext_autoindex_languages();

    IF fulltext_autoindex_languages IS NOT NULL THEN
        FOREACH searchconfig IN ARRAY fulltext_autoindex_languages LOOP
            INSERT INTO fts (nid, config, searchtype, tsvec)
            SELECT NEW.id, searchconfig, 'fulltext', to_tsvector_safe(searchconfig, NEW.fulltext);
        END LOOP;
    END IF;

    attribute_autoindex_languages = get_attribute_autoindex_languages();

    IF attribute_autoindex_languages IS NOT NULL THEN
        FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
            INSERT INTO fts (nid, config, searchtype, tsvec)
            SELECT NEW.id, searchconfig, 'attrs', jsonb_object_values_to_tsvector(searchconfig, NEW.attrs);
        END LOOP;
    END IF;
RETURN NEW;
END;
$$;


CREATE OR REPLACE FUNCTION update_node_tsvectors() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig text;
    fulltext_autoindex_languages text[];
    attribute_autoindex_languages text[];
BEGIN
    fulltext_autoindex_languages = get_fulltext_autoindex_languages();

    IF fulltext_autoindex_languages IS NOT NULL THEN
        IF OLD.fulltext != NEW.fulltext THEN
            FOREACH searchconfig IN ARRAY fulltext_autoindex_languages LOOP
                -- TODO: replace with proper upsert after 9.5
                DELETE FROM fts
                WHERE nid = NEW.id AND config = searchconfig AND searchtype = 'fulltext';
                INSERT INTO fts (nid, config, searchtype, tsvec)
                SELECT NEW.id, searchconfig, 'fulltext', to_tsvector_safe(searchconfig::regconfig, NEW.fulltext);
            END LOOP;
        END IF;
    END IF;

    attribute_autoindex_languages = get_attribute_autoindex_languages();

    IF attribute_autoindex_languages IS NOT NULL THEN
        IF OLD.attrs != NEW.attrs THEN
            FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
                -- TODO: replace with proper upsert after 9.5
                DELETE FROM fts
                WHERE nid = NEW.id AND config = searchconfig AND searchtype = 'attrs';
                INSERT INTO fts (nid, config, searchtype, tsvec)
                SELECT NEW.id, searchconfig, 'attrs', jsonb_object_values_to_tsvector(searchconfig::regconfig, NEW.attrs);
            END LOOP;
        END IF;
    END IF;
RETURN NEW;
END;
$$;


CREATE TRIGGER insert_node_tsvectors AFTER INSERT
ON :search_path.node FOR EACH ROW EXECUTE PROCEDURE insert_node_tsvectors();


CREATE TRIGGER update_node_tsvectors AFTER UPDATE
ON :search_path.node FOR EACH ROW EXECUTE PROCEDURE update_node_tsvectors();


CREATE OR REPLACE FUNCTION to_tsvector_safe(config regconfig, text text) RETURNS tsvector
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    COST 10000000000
    AS $$
DECLARE
    tsvec tsvector;
    exc_text text;
    exc_detail text;
    exc_hint text;
BEGIN
    IF length(text) < 2 THEN
        RETURN NULL;
    END IF;

    BEGIN
        tsvec = to_tsvector(config, text);
    EXCEPTION
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS exc_text = MESSAGE_TEXT,
                                    exc_detail = PG_EXCEPTION_DETAIL,
                                    exc_hint = PG_EXCEPTION_HINT;
            RAISE NOTICE 'exception:  %\n%\nHINT: %', exc_text, exc_detail, exc_hint;

            RETURN NULL;
    END;

    IF tsvec IS NULL OR length(tsvec) = 0 THEN
        RETURN NULL;
    END IF;

    RETURN tsvec;
END;
$$;


CREATE TYPE :search_path.tsvector_with_config AS (config regconfig, tsvec tsvector);
CREATE OR REPLACE FUNCTION shortest_tsvec(_fulltext_id integer, configs regconfig[]) RETURNS :search_path.tsvector_with_config
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    tsvec tsvector;
    min_tsvec tsvector;
    config regconfig;
    min_config regconfig;
    text text;
BEGIN
    SELECT fulltext INTO text FROM fulltext WHERE id=_fulltext_id;

    FOREACH config IN ARRAY configs LOOP
        tsvec = to_tsvector(config, text);
        RAISE NOTICE 'test %, length of tsvector is %', config, length(tsvec);

        IF min_tsvec IS NULL OR length(tsvec) < length(min_tsvec) THEN
            min_tsvec = tsvec;
            min_config = config;
        END IF;
    END LOOP;

RETURN (_fulltext_id, min_config, min_tsvec);
END;
$$;


-- XXX: does not work anymore, nodefile is file + node_to_file now
CREATE OR REPLACE FUNCTION import_fulltexts_multicorn() RETURNS void
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
    DROP TABLE IF EXISTS mediatum_import_fulltexts;

    CREATE TABLE mediatum_import.fulltexts AS
    SELECT nid, string_agg(fulltext, '\n---\n')
    FROM mediatum_import.fulltext_files ft, nodefile nf
    WHERE filetype='fulltext'
    AND path = replace(ft.dir, '.', '/') || '/' || ft.id || '.txt'
    GROUP BY nid
    ;
RETURN;
END;
$$;


CREATE OR REPLACE FUNCTION import_fulltexts_into_node_table() RETURNS void
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
    ALTER TABLE node DISABLE TRIGGER update_node_tsvectors;

    UPDATE node
    SET fulltext=q.fulltext
    FROM (SELECT id, fulltext FROM mediatum_import.fulltexts) q
    WHERE node.id = q.nid;

    ALTER TABLE node ENABLE TRIGGER update_node_tsvectors;
RETURN;
END;
$$;


CREATE OR REPLACE FUNCTION recreate_all_tsvectors_fulltext() RETURNS void
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig regconfig;
    fulltext_autoindex_languages text[];
BEGIN
    fulltext_autoindex_languages = get_fulltext_autoindex_languages();

    IF fulltext_autoindex_languages IS NOT NULL THEN
        DELETE FROM fts WHERE searchtype = 'fulltext';
        FOREACH searchconfig IN ARRAY fulltext_autoindex_languages LOOP
            -- TODO: replace with proper upsert after 9.5
            EXECUTE 'DROP INDEX IF EXISTS fts_fulltext_' || searchconfig;
            INSERT INTO fts (nid, config, searchtype, tsvec)
            SELECT id, searchconfig, 'fulltext', to_tsvector_safe(searchconfig::regconfig, fulltext)
            FROM node WHERE fulltext IS NOT NULL;

            -- rebuild the search index
            EXECUTE 'CREATE INDEX fts_fulltext_' || searchconfig
                || ' ON fts USING gin(tsvec) WHERE config = ''' || searchconfig || ''''
                || ' AND searchtype = ''fulltext''';
        END LOOP;
    END IF;
RETURN;
END;
$$;

CREATE OR REPLACE FUNCTION drop_attrindex_search(attrname text)
    RETURNS text[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig regconfig;
    attribute_autoindex_languages text[];
    idx text;
    dropped text[];
BEGIN
    attribute_autoindex_languages = get_attribute_autoindex_languages();

    IF attribute_autoindex_languages IS NOT NULL THEN
        FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
            idx = 'ix_mediatum_node_attr_search_' || replace(attrname, '-', '_') || '_' || searchconfig;

            IF (SELECT to_regclass(idx::cstring) IS NOT NULL) THEN
                EXECUTE 'DROP INDEX ' || idx;
                RAISE NOTICE 'dropped attribute fts index % (attr:%, searchconfig:%)', idx, attrname, searchconfig;
                dropped = array_append(dropped, searchconfig::text);
            END IF;
        END LOOP;
    END IF;

    RETURN dropped;
END;
$$;


CREATE OR REPLACE FUNCTION create_attrindex_search(attrname text, replace_existing boolean = false)
    RETURNS text[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig regconfig;
    attribute_autoindex_languages text[];
    idx text;
    created text[];
BEGIN
    attribute_autoindex_languages = get_attribute_autoindex_languages();

    IF attribute_autoindex_languages IS NOT NULL THEN
        FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
            idx = 'ix_mediatum_node_attr_search_' || replace(replace(attrname, '-', '_'), '.', '_') || '_' || searchconfig;

            IF replace_existing THEN
                EXECUTE 'DROP INDEX IF EXISTS ' || idx;
            END IF;

            IF (SELECT to_regclass(idx::cstring) IS NULL) THEN
                EXECUTE 'CREATE INDEX ' || idx
                || ' ON node USING gin(to_tsvector_safe(''' || searchconfig
                || ''', replace(attrs ->> ''' || attrname || ''', '';'', '' '')))';
                RAISE NOTICE 'created attribute fts index % (attr:%, searchconfig:%)', idx, attrname, searchconfig;
                created = array_append(created, searchconfig::text);
            END IF;
        END LOOP;
    END IF;

    RETURN created;
END;
$$;


CREATE OR REPLACE FUNCTION recreate_all_tsvectors_attrs() RETURNS void
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig regconfig;
    attribute_autoindex_languages text[];
BEGIN
    attribute_autoindex_languages = get_attribute_autoindex_languages();

    IF attribute_autoindex_languages IS NOT NULL THEN
        DELETE FROM fts WHERE searchtype = 'attrs';
        FOREACH searchconfig IN ARRAY attribute_autoindex_languages LOOP
            -- TODO: replace with proper upsert after 9.5
            EXECUTE 'DROP INDEX IF EXISTS fts_attrs_' || searchconfig;
            INSERT INTO fts (nid, config, searchtype, tsvec)
            SELECT id, searchconfig, 'attrs', jsonb_object_values_to_tsvector(searchconfig::regconfig, attrs)
            FROM node WHERE attrs IS NOT NULL;

            -- rebuild the search index
            EXECUTE 'CREATE INDEX fts_attrs_' || searchconfig
                || ' ON fts USING gin(tsvec) WHERE config = ''' || searchconfig || ''''
                || ' AND searchtype = ''attrs''';
        END LOOP;
    END IF;
RETURN;
END;
$$;
