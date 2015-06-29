-- Table: nodesearch

CREATE OR REPLACE FUNCTION update_nodesearch_tsvec() RETURNS void
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
    UPDATE nodesearch 
    SET fulltext_search = to_tsvector(config, fulltext);
END;
$$;


CREATE OR REPLACE FUNCTION on_nodesearch_update() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
    NEW.fulltext_search = to_tsvector(NEW.config, NEW.fulltext);
RETURN NEW;
END;
$$;

-- CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
-- ON  FOR EACH ROW EXECUTE PROCEDURE on_nodesearch_update();


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


CREATE OR REPLACE FUNCTION create_fts_entry(config regconfig, fulltext_id integer) RETURNS :search_path.fts
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    text text;
    tsvec tsvector;
BEGIN
    SELECT fulltext INTO text FROM fulltext WHERE id=fulltext_id;
    tsvec = to_tsvector_safe(config, text);
    RETURN (fulltext_id, config, tsvec);
END;
$$;


CREATE OR REPLACE FUNCTION shortest_tsvec(_fulltext_id integer, configs regconfig[]) RETURNS :search_path.fts
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


CREATE OR REPLACE FUNCTION py_guess_language(text text) RETURNS text
   LANGUAGE plpython3u
    SET search_path = :search_path
    AS $$

    import guess_language
    try:
        lang = guess_language.guess_language(text)
    except:
        lang = None

    return lang
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
            AND path = replace(imp.dir, '.', '/') || '/' || imp.id || '.txt') q ON true
    ;
RETURN;
END;
$$;



