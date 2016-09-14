-- functions that are used to speed up important parts of mediaTUM.
-- they could all be implemented in Python instead but this is faster ;)

-- Finds all paths to `node_id` that are accessible with the given access params `group_ids`, `ipaddr` and `date`.
-- Node IDs matching `exclude_container_ids` won't be returned.
-- Typically, `node_id` will be an id of a content node that is contained in one or more containers.
CREATE OR REPLACE FUNCTION accessible_container_paths(node_id integer, exclude_container_ids integer[]=ARRAY[]::integer[]
                                                     ,group_ids integer[]=NULL, ipaddr inet=NULL, date date=NULL)
    RETURNS setof integer[]
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
BEGIN
RETURN QUERY SELECT 
    (SELECT array_append(array_agg(q.nid), nm.nid)
     FROM (SELECT nid 
           FROM noderelation nr 
           WHERE nr.cid=nm.nid
           AND has_read_access_to_node(nr.nid, group_ids, ipaddr, date)
           AND NOT ARRAY[nr.nid] <@ exclude_container_ids
           ORDER BY distance DESC) q) as path

    FROM nodemapping nm
    WHERE cid=node_id 
    AND NOT ARRAY[nm.nid] <@ exclude_container_ids
    AND has_read_access_to_node(nm.nid, group_ids, ipaddr, date);
END;
$f$;


CREATE MATERIALIZED VIEW IF NOT EXISTS :search_path.container_info AS 
SELECT 
    id AS nid
    ,(SELECT count(*) FROM :search_path.node JOIN :search_path.noderelation nr ON (id=cid) 
      WHERE nid=no.id 
      AND subnode=false
      AND type IN (SELECT name FROM nodetype WHERE is_container=false)) AS count_content_children_for_all_subcontainers

FROM :search_path.node no WHERE no.type IN (SELECT name FROM nodetype WHERE is_container=true);

-- needed to refresh container_info concurrently
CREATE UNIQUE INDEX ON container_info (nid);

CREATE OR REPLACE FUNCTION count_content_children_for_all_subcontainers(container_id integer)
    RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
DECLARE 
    cc integer;
BEGIN
    SELECT count_content_children_for_all_subcontainers INTO cc FROM container_info WHERE nid=container_id;
    RETURN cc;
END;
$f$;
