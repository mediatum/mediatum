---
-- maintenance
---

-- Deletes unreachable nodes (no path from the root node), their files and connections.
-- Works without transitive node connections.

CREATE OR REPLACE FUNCTION purge_nodes() RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    deleted_nodes integer;
BEGIN
    WITH reachable_node_ids AS (SELECT * FROM subtree_ids(1) UNION ALL SELECT 1),
    del_rel AS (DELETE FROM noderelation
        WHERE nid NOT IN (SELECT * FROM reachable_node_ids)
        OR cid NOT IN (SELECT * FROM reachable_node_ids)),

    del_node AS (DELETE FROM node
        WHERE id NOT IN (SELECT * FROM reachable_node_ids) RETURNING *)

    SELECT count(*) INTO deleted_nodes FROM del_node;
    RETURN deleted_nodes;
END;
$f$;


CREATE OR REPLACE FUNCTION delete_nodes(node_ids integer[], recursive bool = false) RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    deleted_nodes integer;
    subtree_ids integer[];
    ids_to_delete integer[];
BEGIN

    IF recursive THEN
        SELECT array_agg(cid) INTO subtree_ids FROM noderelation WHERE nid IN (SELECT unnest(node_ids));
        ids_to_delete = array_cat(subtree_ids, node_ids);
        SET CONSTRAINTS ALL DEFERRED;
    ELSE
        ids_to_delete = node_ids;
    END IF;

    WITH del_rel AS
       (DELETE FROM nodemapping
        WHERE cid IN (SELECT unnest(ids_to_delete))
        RETURNING cid AS id),

    del_node AS
        (DELETE FROM node
        WHERE id IN (SELECT * FROM del_rel)
        RETURNING *)

    SELECT count(*) INTO deleted_nodes FROM del_node;
    RETURN deleted_nodes;
END;
$f$;


