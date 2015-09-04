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
       (DELETE FROM noderelation
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


CREATE OR REPLACE FUNCTION clean_trash_dirs() RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    trash_item_ids integer[];
    deleted_nodes integer;
BEGIN
    SELECT array_agg(cid)
    INTO trash_item_ids
    FROM nodemapping WHERE nid IN
        (SELECT id
        FROM node JOIN noderelation ON id=cid
        WHERE distance = 2
        AND nid=(SELECT id from node WHERE type = 'home')
        AND name = 'Papierkorb');

    deleted_nodes = delete_nodes(trash_item_ids, true);
    RETURN deleted_nodes;
END;
$f$;



CREATE OR REPLACE FUNCTION purge_empty_home_dirs() RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    deleted_nodes integer;
    home_dir_ids integer[];
    special_dir_ids integer[];
BEGIN
    -- delete empty special dirs first
    SELECT array_agg(id)
    INTO special_dir_ids
    FROM node n JOIN noderelation nr ON id=cid
    WHERE distance = 2
    AND nid=(SELECT id from node WHERE type = 'home')
    AND n.name in ('Papierkorb',
                   'Inkonsistente Daten',
                   'Uploads',
                   'Importe')
    AND id NOT IN (SELECT nid FROM nodemapping);

    PERFORM delete_nodes(special_dir_ids);

    -- delete all now empty home dirs
    SELECT array_agg(id)
    INTO home_dir_ids
    FROM node JOIN nodemapping ON id=cid
    AND nid=(SELECT id from node WHERE type = 'home')
    AND name LIKE 'Arbeitsverzeichnis (%'
    AND id NOT IN (SELECT nid FROM nodemapping);

    UPDATE mediatum.user
    SET home_dir_id=NULL
    WHERE home_dir_id IN (SELECT unnest(home_dir_ids));

    deleted_nodes = delete_nodes(home_dir_ids);
    RETURN deleted_nodes;
END;
$f$;

