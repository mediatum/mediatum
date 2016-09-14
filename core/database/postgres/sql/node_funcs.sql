-- should be extended to a size limit function that also works for other JSON data types
CREATE OR REPLACE FUNCTION jsonb_limit_to_size(input jsonb, bytesize integer = 2000) 
    RETURNS jsonb
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
DECLARE
    res jsonb;
    json_type text = jsonb_typeof(input);
BEGIN
    CASE json_type
        WHEN 'string' THEN
            -- well, not really bytes, but this will work for now ;)
            -- #>>'{}' converts JSONB to a string (really!)
            res := to_jsonb(substr(input#>>'{}', 0, bytesize + 1));
        ELSE
            res := input;
    END CASE;

    RETURN res;
END;
$f$;


CREATE OR REPLACE FUNCTION drop_attrindex_sort(attrname text) 
    RETURNS text[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    idx text;
    idx_desc text;
    dropped text[];
BEGIN
    idx = 'ix_mediatum_node_attr_sort_' || replace(replace(attrname, '.', '_'), '-', '_');
    idx_desc = idx || '_desc';


    IF (SELECT to_regclass(idx::cstring) IS NOT NULL) THEN
        EXECUTE 'DROP INDEX ' || idx;
        dropped = array_append(dropped, 'asc');
    END IF;

    IF (SELECT to_regclass(idx_desc::cstring) IS NOT NULL) THEN
        EXECUTE 'DROP INDEX ' || idx_desc;
        dropped = array_append(dropped, 'desc');
    END IF;

    RETURN dropped;
END;
$f$;


CREATE OR REPLACE FUNCTION create_attrindex_sort(attrname text, replace_existing boolean = false) 
    RETURNS text[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    idx text;
    idx_desc text;
    created text[];
BEGIN
    idx = 'ix_mediatum_node_attr_sort_' || replace(replace(attrname, '.', '_'), '-', '_');
    idx_desc = idx || '_desc';

    IF replace_existing THEN
        EXECUTE 'DROP INDEX IF EXISTS ' || idx;
        EXECUTE 'DROP INDEX IF EXISTS ' || idx_desc;
    END IF;

    IF (SELECT to_regclass(idx::cstring) IS NULL) THEN
        EXECUTE 'CREATE INDEX ' || idx
        || ' ON node ((jsonb_limit_to_size(attrs->''' || attrname || ''')) NULLS LAST, id DESC)';
        RAISE NOTICE 'created attribute sort index % (attr:%)', idx, attrname;
        created = array_append(created, 'asc');
    END IF;

    IF (SELECT to_regclass(idx_desc::cstring) IS NULL) THEN
        EXECUTE 'CREATE INDEX ' || idx_desc
        || ' ON node ((jsonb_limit_to_size(attrs->''' || attrname || ''')) DESC NULLS LAST, id DESC)';
        RAISE NOTICE 'created attribute sort index % (attr:%)', idx_desc, attrname;
        created = array_append(created, 'desc');
    END IF;
    
    RETURN created;
END;
$f$;


CREATE TYPE value_and_count AS (value text, count bigint);
CREATE OR REPLACE FUNCTION count_list_values_for_all_content_children(parent_id integer,attr text) RETURNS setof value_and_count
    LANGUAGE plpgsql
    STABLE
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


CREATE OR REPLACE FUNCTION get_list_values_for_nodes_with_schema(schema_ text, attr text) RETURNS setof text
    LANGUAGE plpgsql
    STABLE
    SET search_path = :search_path
    AS $f$
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
$f$;

