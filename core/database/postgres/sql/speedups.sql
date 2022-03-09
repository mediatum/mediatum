-- functions that are used to speed up important parts of mediaTUM.
-- they could all be implemented in Python instead but this is faster ;)

-- Finds all paths to `node_id` that are accessible with the given access params `group_ids`, `ipaddr` and `date`.
-- Node IDs matching `exclude_container_ids` won't be returned.
-- Typically, `node_id` will be an id of a content node that is contained in one or more containers.
CREATE OR REPLACE FUNCTION mediatum.accessible_container_paths(node_id integer, group_ids integer[] DEFAULT NULL::integer[], ipaddr inet DEFAULT NULL::inet, date date DEFAULT NULL::date)
 RETURNS SETOF integer[][]
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path = :search_path
AS $f$
BEGIN
RETURN QUERY
    WITH RECURSIVE paths(path) AS
    (
            SELECT ARRAY[ARRAY[nodemapping.nid, has_read_access_to_node(nodemapping.nid, group_ids, ipaddr, date)::int]]
            FROM nodemapping
            WHERE nodemapping.cid = node_id
        UNION ALL
            SELECT ARRAY[nodemapping.nid, has_read_access_to_node(nodemapping.nid, group_ids, ipaddr, date)::int] || paths.path
            FROM nodemapping
            JOIN paths ON nodemapping.cid = paths.path[1][1]
    )
    SELECT path
    FROM paths WHERE
    NOT EXISTS (SELECT FROM nodemapping WHERE cid = path[1][1]);
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
