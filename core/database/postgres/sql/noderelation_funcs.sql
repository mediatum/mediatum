CREATE OR REPLACE FUNCTION searchpath() RETURNS text
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    ret text;

BEGIN
    SELECT setting into ret from pg_settings where name = 'search_path';
    RETURN ret;
END;
$f$;


-- Returns ids for nodes in the "subtree" (DAG) below `root_id`
CREATE OR REPLACE FUNCTION subtree_ids(root_id integer) RETURNS SETOF integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE s(parent_id) AS (
		SELECT cid as parent_id 
		FROM nodemapping
		WHERE nid = root_id
	UNION ALL
		SELECT cid 
		FROM s, nodemapping
		WHERE nid = parent_id
	)
	SELECT * FROM s;
END;
$f$;

-- "Cuts" out a subtree from the tree (= DAG...) starting with `root_id`
CREATE OR REPLACE FUNCTION subtree_relation(root_id integer) RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    STABLE
    AS $f$
BEGIN
    RETURN QUERY
    -- ids of all nodes in the subtree
    WITH s AS (
        SELECT cid as id
        FROM noderelation
        WHERE nid = root_id
    UNION ALL
        SELECT root_id as id
    )
    SELECT nid, cid, distance
    FROM noderelation, s
    WHERE nid = s.id;
END;
$f$;

-- "Cuts" out a subtree from the tree (= DAG...) starting with `root_id` limited to a depth of `max_distance`
CREATE OR REPLACE FUNCTION subtree_relation(root_id integer, max_distance integer) RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    STABLE
    AS $f$
BEGIN
    RETURN QUERY
    -- ids of all nodes in the subtree
    WITH s AS (
        SELECT cid as id, distance
        FROM noderelation
        WHERE nid = root_id
        AND distance <= max_distance
    UNION ALL
        SELECT root_id, 0 as id
    )
    SELECT nr.nid, nr.cid, nr.distance
    FROM noderelation nr, s
    WHERE nid = s.id
    AND nr.distance + s.distance <= max_distance;
END;
$f$;


-- Returns the full set of transitive connections between nodes 
-- for the DAG specified by connections with distance = 1
CREATE OR REPLACE FUNCTION transitive_closure() RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE t(nid, cid, distance) AS (
		SELECT nid, cid, distance
		FROM noderelation
		WHERE distance = 1

	UNION ALL
		SELECT t.nid, nr.cid, t.distance + 1
		FROM t, noderelation nr
		WHERE t.cid = nr.nid
		AND nr.distance = 1
	)
	SELECT * FROM t;
END;
$f$;


-- Returns the full set of transitive connections between nodes 
-- for the DAG specified by connections with distance = 1
-- Direct connections (distance = 1) are not included.
CREATE OR REPLACE FUNCTION transitive_closure_without_direct_connections() RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE t(nid, cid, distance) AS (
		SELECT n1.nid, n2.cid, 2
		FROM noderelation n1, noderelation n2
		WHERE n1.cid = n2.nid
		AND n1.distance = 1
		AND n2.distance = 1

	UNION ALL
		SELECT t.nid, nr.cid, t.distance + 1
		FROM t, noderelation nr
		WHERE t.cid = nr.nid
		AND nr.distance = 1
	)
	SELECT * FROM t;
END;
$f$;


-- Returns transitive connections for from the node with `node_id` to the root 
CREATE OR REPLACE FUNCTION transitive_closure_for_node(node_id integer) RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql STABLE
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE t(nid, cid, distance) AS (
		SELECT *
		FROM noderelation
		WHERE distance = 1
		AND cid = node_id

	UNION ALL
		SELECT nr.nid, node_id, t.distance + 1
		FROM t, noderelation nr
		WHERE t.nid = nr.cid
		AND nr.distance = 1
	)
	SELECT * FROM t;
END;
$f$;


-- Returns transitive connections for from the node with `node_id` to the root,
-- excluding connections through the node `excluded_id`
CREATE OR REPLACE FUNCTION transitive_closure_for_node_excluding(node_id integer, excluded_id integer) RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql STABLE
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE t(nid, cid, distance) AS (
		SELECT *
		FROM noderelation
		WHERE distance = 1
		AND cid = node_id
		AND nid != excluded_id

	UNION ALL
		SELECT nr.nid, t.cid, t.distance + 1
		FROM t, noderelation nr
		WHERE t.nid = nr.cid
		AND nr.distance = 1
		AND nr.nid != excluded_id
	)
	SELECT * FROM t;
END;
$f$;


-- Takes a direct connection from `parent_id` and `child_id` 
-- and adds all (transitive and direct) connections to the parent with incremented distance
-- In other words: the connection from `parent_id` to `child_id` is added to all paths reaching `parent_id`
CREATE OR REPLACE FUNCTION extend_relation_to_parents(parent_id integer, child_id integer) RETURNS SETOF :search_path.noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    STABLE
    AS $f$
BEGIN
RETURN QUERY
    SELECT nid, child_id, distance + 1 
    FROM noderelation 
    WHERE cid = parent_id
    UNION
    SELECT parent_id, child_id, 1;
END;
$f$;


-- Returns all paths reaching the nodes ins `start_ids` starting at the root as table of node id arrays
CREATE OR REPLACE FUNCTION paths(start_ids integer[]) RETURNS TABLE(path integer[])
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE p(path) AS
		(SELECT ARRAY[nid] as path
		FROM noderelation
		WHERE start_ids @> ARRAY[cid]
		AND distance = 1

	UNION ALL 

	SELECT nid || p.path as path
	FROM p, noderelation nr
	WHERE p.path[1] = nr.cid
	AND distance = 1
	)
	SELECT * FROM p;
END;
$f$;


-- Returns all paths reaching `node_id` starting at the root as table of node id arrays
CREATE OR REPLACE FUNCTION paths(node_id integer) RETURNS TABLE(path integer[])
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE p(path) AS
		(SELECT ARRAY[nid] as path
		FROM noderelation
		WHERE cid = node_id
		AND distance = 1

	UNION ALL 

	SELECT nid || p.path as path
	FROM p, noderelation nr
	WHERE p.path[1] = nr.cid
	AND distance = 1
	)
	SELECT * FROM p;
END;
$f$;


-- Returns all paths reaching `node_id` starting at the root as table of node id arrays. 
-- Paths running through `excluded_id` are ignored.
CREATE OR REPLACE FUNCTION paths_to_node_excluding(node_id integer, excluded_id integer) RETURNS TABLE(path integer[])
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RETURN QUERY
	WITH RECURSIVE p(path) AS
		(SELECT ARRAY[nid] as path
		FROM noderelation
		WHERE cid = node_id
		AND distance = 1
		AND nid != excluded_id

	UNION ALL 

	SELECT nid || p.path as path
	FROM p, noderelation nr
	WHERE p.path[1] = nr.cid
	AND distance = 1
	AND nid != excluded_id
	)
	SELECT * FROM p;
END;
$f$;


-- Recalculate all connections for nodes under `root_id`
CREATE OR REPLACE FUNCTION recalculate_relation_subtree(root_id integer, OUT inserted integer, OUT deleted integer, OUT affected_relations integer) RETURNS record
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
	rel RECORD;
	ins integer;
	del integer;
BEGIN

deleted := 0;
inserted := 0;
affected_relations := 0;

-- LOCK TABLE noderelation IN EXCLUSIVE MODE;

-- check all connections to children of root
FOR rel IN SELECT cid, distance FROM noderelation WHERE nid = root_id LOOP
    
    -- RAISE NOTICE 'DELETE FROM noderelation nr WHERE nr.cid = % AND nr.distance > %', rel.cid, rel.distance;

	-- only delete tuples belonging to paths which could go through root_id
	DELETE FROM noderelation nr 
	WHERE nr.cid = rel.cid 
	AND nr.distance > rel.distance
	;
	GET DIAGNOSTICS del = ROW_COUNT;

    -- RAISE NOTICE 'INSERT INTO noderelation SELECT DISTINCT * FROM transitive_closure_for_node(%)', rel.cid;

	INSERT INTO noderelation
    SELECT DISTINCT * FROM transitive_closure_for_node(rel.cid)
	WHERE distance > rel.distance
    ;
	 GET DIAGNOSTICS ins = ROW_COUNT;

	RAISE NOTICE 'cid % distance %, deleted %, inserted %', rel.cid, rel.distance, del, ins;
    
    PERFORM update_inherited_access_rules_for_node(rel.cid);
	
	inserted := inserted + ins;
	deleted := deleted + del;
	affected_relations := affected_relations + 1;

END LOOP;
END;
$f$;


CREATE OR REPLACE FUNCTION on_mapping_insert() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN
RAISE NOTICE 'insert mapping % -> %', NEW.nid, NEW.cid;

-- check if parent is a content node (is_container = false)
IF (SELECT type IN (SELECT name FROM nodetype WHERE is_container = false) FROM node WHERE id=NEW.nid) THEN
    RAISE NOTICE 'parent is content';

    -- should fail if someone wants to add a container as child of a content node
    IF (SELECT type IN (SELECT name FROM nodetype WHERE is_container = true) FROM node WHERE id=NEW.cid) THEN
        RAISE EXCEPTION 'cannot add a container child to a content parent!';
    END IF;
    -- set subnode attribute because we are adding a content node as child of another content node
    UPDATE node SET subnode = true WHERE id = NEW.cid;
END IF;

-- copy connections from new parent (nid)
INSERT INTO noderelation 
SELECT * FROM extend_relation_to_parents(NEW.nid, NEW.cid) f
WHERE NOT EXISTS(SELECT FROM noderelation WHERE nid=f.nid AND cid=f.cid AND distance=f.distance);

PERFORM update_inherited_access_rules_for_node(NEW.cid);
PERFORM recalculate_relation_subtree(NEW.cid);

RETURN NEW;
END;
$f$;


CREATE OR REPLACE FUNCTION on_mapping_delete() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
BEGIN

RAISE NOTICE 'remove mapping % -> %', OLD.nid, OLD.cid;

-- delete all transitive relations ending at cid
-- ! we delete connections here that are still correct
-- re-add them later
DELETE FROM noderelation 
WHERE cid = OLD.cid AND distance > 1;

-- delete direct connection between nid and cid
DELETE FROM noderelation 
WHERE cid = OLD.cid
AND nid = OLD.nid;

-- re-add incoming transitive connections to `cid`
INSERT INTO noderelation
SELECT DISTINCT * FROM transitive_closure_for_node(OLD.cid) WHERE distance > 1;
-- recalculate connections to the subtree under `cid` (all paths going through `cid`)
PERFORM update_inherited_access_rules_for_node(OLD.cid);
PERFORM recalculate_relation_subtree(OLD.cid);

-- check if old parent and child are content nodes (is_container = false)
IF (SELECT type IN (SELECT name FROM nodetype WHERE is_container = false) FROM node WHERE id=OLD.nid)
AND (SELECT type IN (SELECT name FROM nodetype WHERE is_container = false) FROM node WHERE id=OLD.cid) THEN
    -- and child is orphaned now
    IF (SELECT NOT EXISTS (SELECT FROM nodemapping WHERE cid=OLD.cid)) THEN
        UPDATE node SET subnode = false WHERE id = OLD.cid;
    END IF;
END IF;


RETURN OLD;
END;
$f$;


CREATE OR REPLACE FUNCTION is_descendant_of(descendant_id integer, node_id integer) RETURNS bool
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    res bool;
BEGIN
    SELECT INTO res EXISTS (SELECT FROM noderelation WHERE nid=node_id AND cid=descendant_id);
    RETURN res;
END;
$f$;
