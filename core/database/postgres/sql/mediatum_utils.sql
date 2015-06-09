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
    del_file AS (DELETE FROM nodefile
        WHERE nid NOT IN (SELECT * FROM reachable_node_ids)),
       
    del_rel AS (DELETE FROM noderelation
        WHERE nid NOT IN (SELECT * FROM reachable_node_ids)
        OR cid NOT IN (SELECT * FROM reachable_node_ids)),
        
    del_nodes AS (DELETE FROM node
        WHERE id NOT IN (SELECT * FROM reachable_node_ids) RETURNING *)
    SELECT count(*) INTO deleted_nodes FROM del_nodes;

    RETURN deleted_nodes;
END;
$f$;
