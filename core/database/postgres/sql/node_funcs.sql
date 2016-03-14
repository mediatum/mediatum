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


CREATE TYPE value_and_count AS (value text, count bigint);
CREATE OR REPLACE FUNCTION count_list_values_for_all_content_children(parent_id integer,attr text) RETURNS setof value_and_count
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
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
$f$;

