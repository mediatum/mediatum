CREATE OR REPLACE FUNCTION insert_node_tsvectors() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    searchconfig regconfig;
    autoindex_languages text[];
BEGIN
    SELECT array_agg(v)
    FROM (SELECT jsonb_array_elements_text(value) v FROM setting WHERE key = 'search.autoindex_languages') q
    INTO autoindex_languages;

    IF autoindex_languages IS NOT NULL THEN
        FOREACH searchconfig IN ARRAY autoindex_languages LOOP
            INSERT INTO fts (nid, config, searchtype, tsvec)
            SELECT NEW.id, searchconfig, 'fulltext', to_tsvector_safe(searchconfig, NEW.fulltext);

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
    autoindex_languages text[];
BEGIN
    SELECT array_agg(v)
    FROM (SELECT jsonb_array_elements_text(value) v FROM setting WHERE key = 'search.autoindex_languages') q
    INTO autoindex_languages;

    IF autoindex_languages IS NOT NULL THEN
        IF OLD.fulltext != NEW.fulltext THEN
            FOREACH searchconfig IN ARRAY autoindex_languages LOOP
                -- TODO: replace with proper upsert after 9.5
                DELETE FROM fts
                WHERE nid = NEW.id AND config = searchconfig AND searchtype = 'fulltext';
                INSERT INTO fts (nid, config, searchtype, tsvec)
                SELECT NEW.id, searchconfig, 'fulltext', to_tsvector_safe(searchconfig::regconfig, NEW.fulltext);
            END LOOP;
        END IF;

        IF OLD.attrs != NEW.attrs THEN
            FOREACH searchconfig IN ARRAY autoindex_languages LOOP
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
    IF length(text) < 4 THEN
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


CREATE OR REPLACE FUNCTION import_fulltexts() RETURNS void
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    min_config regconfig;
BEGIN
    INSERT INTO fulltext (fulltext, nid)
    SELECT fulltext, q.nid
    FROM mediatum_import.fulltexts imp
    JOIN LATERAL (SELECT id AS nid
            FROM node JOIN nodefile nf ON node.id=nf.nid
            WHERE filetype='fulltext'
            AND path = replace(imp.dir, '.', '/') || '/' || imp.id || '.txt') q ON true;
RETURN;
END;
$$;

