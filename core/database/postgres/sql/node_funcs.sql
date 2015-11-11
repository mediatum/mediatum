CREATE OR REPLACE FUNCTION create_attr_index(attr text) RETURNS boolean
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    idx text;
    idx_nulls_last text;
    created boolean = false;
BEGIN
    idx = 'ix_mediatum_node_attr_' || replace(replace(attr, '.', '_'), '-', '_');
    idx_nulls_last = idx || '_nulls_last';


    IF (SELECT to_regclass(idx::cstring) IS NULL) THEN
        EXECUTE 'CREATE INDEX ' || idx
        || ' ON node ((attrs->''' || attr || '''))';
        RAISE NOTICE 'created index %', idx; 
        created = true;
    END IF;

    IF (SELECT to_regclass(idx_nulls_last::cstring) IS NULL) THEN
        EXECUTE 'CREATE INDEX ' || idx || '_nulls_last'
        || ' ON node ((attrs->''' || attr || ''') NULLS LAST)';
        RAISE NOTICE 'created index %', idx_nulls_last; 
        created = true;
    END IF;

    RETURN created;
END;
$f$;
