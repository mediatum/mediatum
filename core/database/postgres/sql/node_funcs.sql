CREATE OR REPLACE FUNCTION create_attr_sort_index(attr text) RETURNS boolean
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    idx text;
    idx_desc text;
    created boolean = false;
BEGIN
    idx = 'ix_mediatum_node_attr_' || replace(replace(attr, '.', '_'), '-', '_');
    idx_desc = idx || '_desc';


    IF (SELECT to_regclass(idx::cstring) IS NULL) THEN
        EXECUTE 'CREATE INDEX ' || idx
        || ' ON node ((attrs->''' || attr || '''), id DESC)';
        RAISE NOTICE 'created index %', idx; 
        created = true;
    END IF;

    IF (SELECT to_regclass(idx_desc::cstring) IS NULL) THEN
        EXECUTE 'CREATE INDEX ' || idx_desc
        || ' ON node ((attrs->''' || attr || ''') DESC NULLS LAST, id DESC)';
        RAISE NOTICE 'created index %', idx_desc; 
        created = true;
    END IF;

    RETURN created;
END;
$f$;

