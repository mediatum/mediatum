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
            -- RAISE DEBUG 'exception:  %\n%\nHINT: %', exc_text, exc_detail, exc_hint;

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
        -- RAISE DEBUG 'test %, length of tsvector is %', config, length(tsvec);

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
