CREATE OR REPLACE FUNCTION check_access_rule(rule access_rule, _group_ids integer[], ipaddr inet, _date date) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN 
    (rule.subnets IS NULL OR ipaddr IS NULL OR (rule.invert_subnet != (ipaddr <<= ANY(rule.subnets))))
    AND (rule.group_ids IS NULL OR _group_ids IS NULL OR (rule.invert_group != (_group_ids && rule.group_ids)))
    AND (rule.dateranges IS NULL OR _date IS NULL OR (rule.invert_date != (_date <@ ANY(rule.dateranges))));
END;
$f$;


--
-- functions that determine if the current user (in groups `group_ids`) from ipaddr has access to `node_id` on the given date
--

CREATE OR REPLACE FUNCTION _has_read_type_access_to_node(node_id integer, _ruletype text, _group_ids integer[], ipaddr inet, _date date) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN EXISTS (
    SELECT FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND node.id = node_id
    AND na.invert != check_access_rule(a, _group_ids, ipaddr, _date));
END;
$f$;


CREATE OR REPLACE FUNCTION has_read_access_to_node(node_id integer, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    COST 100000
    STABLE
AS $f$
BEGIN
    RETURN _has_read_type_access_to_node(node_id, 'read', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION has_data_access_to_node(node_id integer, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
    RETURN _has_read_type_access_to_node(node_id, 'data', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION _has_write_type_access_to_node(node_id integer, _ruletype text, _group_ids integer[], ipaddr inet, _date date) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN EXISTS (
    SELECT node.id FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.blocking = false
    AND node.id = node_id
    AND na.invert != check_access_rule(a, _group_ids, ipaddr, _date)

    EXCEPT

    SELECT node.id FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.blocking = true
    AND node.id = node_id
    AND NOT na.invert != check_access_rule(a, _group_ids, ipaddr, _date));

END;
$f$;


CREATE OR REPLACE FUNCTION has_write_access_to_node(node_id integer, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
    RETURN _has_write_type_access_to_node(node_id, 'write', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION _read_type_accessible_nodes(_ruletype text, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL)
    RETURNS SETOF node
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
DECLARE
    r node;
BEGIN
RETURN QUERY
    SELECT node.* FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.invert != check_access_rule(a, _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION read_accessible_nodes(_group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
    RETURN QUERY SELECT * FROM _read_type_accessible_nodes('read', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION data_accessible_nodes(_group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
    RETURN QUERY SELECT * FROM _read_type_accessible_nodes('data', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION _write_type_accessible_nodes(_ruletype text, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY
    SELECT node.* FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.blocking = false
    AND na.invert != check_access_rule(a, _group_ids, ipaddr, _date)

    EXCEPT

    SELECT node.* FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.blocking = true
    AND NOT na.invert != check_access_rule(a, _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION write_accessible_nodes(_group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
    RETURN QUERY SELECT * FROM _write_type_accessible_nodes('write', _group_ids, ipaddr, _date);
END;
$f$;


--
-- update functions
--

-- blocking is not supported for read-type access rules, so the blocking attribute is always returned as NULL
CREATE OR REPLACE FUNCTION _inherited_access_rules_read_type(node_id integer, _ruletype text) 
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
IF EXISTS (SELECT FROM node_to_access_rule WHERE nid=node_id AND ruletype=_ruletype AND inherited = false) THEN
    RETURN;
END IF;

RETURN QUERY
    SELECT DISTINCT node_id AS nid, rule_id, _ruletype,
      (SELECT invert
       FROM node_to_access_rule na
       WHERE na.nid=q.nid
         AND na.rule_id=q.rule_id
        AND na.ruletype=_ruletype) as inverted, 
        TRUE AS inherited, FALSE AS blocking
    FROM (WITH RECURSIVE ra(nid, rule_ids) AS
            (SELECT nm.nid,
               (SELECT array_agg(rule_id) AS rule_ids
                FROM node_to_access_rule na
                WHERE nid=nm.nid
                  AND na.ruletype=_ruletype)
             FROM nodemapping nm
             WHERE nm.cid = node_id
             UNION ALL SELECT nm.nid,
               (SELECT array_agg(rule_id) AS rule_ids
                FROM node_to_access_rule na
                WHERE nid=nm.nid
                  AND na.ruletype=_ruletype)
             FROM nodemapping nm,
                              ra
             WHERE nm.cid = ra.nid
               AND ra.rule_ids IS NULL)
          SELECT DISTINCT nid,
                          unnest(rule_ids) AS rule_id
          FROM ra) q;
END;
$f$;


CREATE OR REPLACE FUNCTION inherited_access_rules_read(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY SELECT * FROM _inherited_access_rules_read_type(node_id, 'read');
END;
$f$;


CREATE OR REPLACE FUNCTION inherited_access_rules_data(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY SELECT * FROM _inherited_access_rules_read_type(node_id, 'data');
END;
$f$;


CREATE OR REPLACE FUNCTION create_all_inherited_access_rules_read()
    RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    INSERT INTO node_to_access_rule 
    SELECT i.* FROM node 
    JOIN LATERAL inherited_access_rules_read(node.id) i ON TRUE 
    WHERE node.id NOT IN (SELECT nid FROM node_to_access_rule WHERE ruletype='read');
END;
$f$;


CREATE OR REPLACE FUNCTION create_all_inherited_access_rules_data()
    RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    INSERT INTO node_to_access_rule 
    SELECT i.* FROM node 
    JOIN LATERAL inherited_access_rules_data(node.id) i ON TRUE 
    WHERE node.id NOT IN (SELECT nid FROM node_to_access_rule WHERE ruletype='data');
END;
$f$;


CREATE OR REPLACE FUNCTION inherited_access_rules_write(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY
    SELECT DISTINCT node_id AS nid,
                    na.rule_id,
                    'write' AS ruletype,
                    na.invert,
                    TRUE AS inherited,
                    na.blocking
    FROM noderelation nr
    JOIN node_to_access_rule na ON nr.nid=na.nid
    WHERE cid=node_id
      AND ruletype = 'write';
END;
$f$;


CREATE OR REPLACE FUNCTION create_all_inherited_access_rules_write()
    RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    -- XXX: very strange: this fails when trying to insert directy into the node_to_access table
    -- this solution with a temp table works
    CREATE TEMPORARY TABLE temp_create_all_inherited_access_rules_write AS
    SELECT i.* FROM node 
    JOIN LATERAL inherited_access_rules_write(node.id) i ON TRUE;

    INSERT INTO node_to_access_rule 
    SELECT DISTINCT * FROM temp_create_all_inherited_access_rules_write t
    WHERE NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=t.nid AND rule_id=t.rule_id AND ruletype='write');
    
END;
$f$;

CREATE TYPE integrity_check_inherited_access_rules AS (nid integer, rule_id integer, ruletype text, invert boolean, blocking boolean, reason text);


CREATE OR REPLACE FUNCTION integrity_check_inherited_access_rules()
    RETURNS SETOF integrity_check_inherited_access_rules
    LANGUAGE plpgsql
    STABLE
    SET search_path TO :search_path
AS $f$
BEGIN
RETURN QUERY
    WITH expected_rules AS (
        SELECT i.* FROM node JOIN LATERAL inherited_access_rules_read(node.id) i ON TRUE
        UNION ALL
        SELECT i.* FROM node JOIN LATERAL inherited_access_rules_write(node.id) i ON TRUE
        UNION ALL
        SELECT i.* FROM node JOIN LATERAL inherited_access_rules_data(node.id) i ON TRUE
    )
    , missing AS (SELECT nid, rule_id, ruletype, invert, blocking FROM expected_rules 
           EXCEPT SELECT nid, rule_id, ruletype, invert, blocking FROM node_to_access_rule)
    , excess AS (SELECT nid, rule_id, ruletype, invert, blocking FROM node_to_access_rule WHERE inherited=true 
          EXCEPT SELECT nid, rule_id, ruletype, invert, blocking FROM expected_rules)

    (SELECT *, 'missing' FROM missing)
    UNION ALL
    (SELECT *, 'excess' FROM excess);
END;
$f$;


CREATE OR REPLACE FUNCTION update_inherited_access_rules_for_node(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    DELETE FROM node_to_access_rule WHERE nid=node_id AND inherited = true;
RETURN QUERY
    INSERT INTO node_to_access_rule 
        SELECT * FROM inherited_access_rules_read(node_id)
        UNION ALL
        SELECT * FROM inherited_access_rules_write(node_id)
        UNION ALL
        SELECT * FROM inherited_access_rules_data(node_id)
    ON CONFLICT DO NOTHING
    RETURNING *;
END;
$f$;


--- trigger functions for access rules


CREATE OR REPLACE FUNCTION on_node_to_access_rule_insert_delete()
    RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
DECLARE
    c record;
    rec node_to_access_rule;
BEGIN

IF TG_OP = 'INSERT' THEN
    rec = NEW;
ELSE
    rec = OLD;
END IF;
IF rec.ruletype IN ('read', 'data') THEN
    FOR c IN SELECT cid FROM noderelation WHERE nid = rec.nid LOOP
        RAISE NOTICE 'updating access rules for node %', c;
        -- ignore nodes that have their own access rules
        IF NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=c.cid AND ruletype = rec.ruletype AND inherited = false) THEN
            DELETE FROM node_to_access_rule WHERE nid=c.cid AND inherited = true AND ruletype = rec.ruletype;
            INSERT INTO node_to_access_rule SELECT * from _inherited_access_rules_read_type(c.cid, rec.ruletype);
        END IF;
    END LOOP;
ELSE
    FOR c in SELECT cid FROM noderelation WHERE nid = rec.nid LOOP
        DELETE FROM node_to_access_rule WHERE nid = c.cid AND inherited = true AND ruletype = rec.ruletype;
        
        INSERT INTO node_to_access_rule 
        SELECT * from inherited_access_rules_write(c.cid) t
        WHERE NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=t.nid AND rule_id=t.rule_id AND ruletype='write');
    END LOOP;
END IF;
RETURN NULL;
END;
$f$;

----
-- ruleset functions
----

CREATE OR REPLACE FUNCTION inherited_access_rulesets_read_type(node_id integer, _ruletype text) 
    RETURNS SETOF node_to_access_ruleset
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
IF EXISTS (SELECT FROM node_to_access_ruleset WHERE nid=node_id AND ruletype=_ruletype) THEN
    RETURN;
END IF;

IF EXISTS (SELECT FROM node_to_access_rule WHERE nid=node_id AND ruletype=_ruletype AND inherited = false) THEN
    RETURN;
END IF;

RETURN QUERY
    SELECT DISTINCT node_id AS nid, ruleset_name, _ruletype,
      (SELECT invert
       FROM node_to_access_ruleset na
       WHERE na.nid=q.nid
        AND na.ruleset_name=q.ruleset_name
        AND na.ruletype=_ruletype) as invert,
      (SELECT blocking
       FROM node_to_access_ruleset na
       WHERE na.nid=q.nid
        AND na.ruleset_name=q.ruleset_name
        AND na.ruletype=_ruletype) as blocking,
      (SELECT private
       FROM node_to_access_ruleset na
       WHERE na.nid=q.nid
        AND na.ruleset_name=q.ruleset_name
        AND na.ruletype=_ruletype) as private 
    FROM (WITH RECURSIVE ra(nid, ruleset_names, rule_ids) AS
            (SELECT nm.nid,
               (SELECT array_agg(ruleset_name) AS ruleset_names
                FROM node_to_access_ruleset na
                WHERE nid=nm.nid
                  AND na.ruletype=_ruletype),

               (SELECT array_agg(rule_id) AS rule_ids
                FROM node_to_access_rule na
                WHERE nid=nm.nid
                  AND na.ruletype=_ruletype
                  AND na.inherited = false)

             FROM nodemapping nm
             WHERE nm.cid = node_id

             UNION ALL SELECT nm.nid,
               (SELECT array_agg(ruleset_name) AS ruleset_names
                FROM node_to_access_ruleset na
                WHERE nid=nm.nid
                  AND na.ruletype=_ruletype),

               (SELECT array_agg(rule_id) AS rule_ids
                FROM node_to_access_rule na
                WHERE nid=nm.nid
                  AND na.ruletype=_ruletype
                  AND na.inherited = false)

             FROM nodemapping nm,
                              ra
             WHERE nm.cid = ra.nid
               AND ra.ruleset_names IS NULL AND ra.rule_ids IS NULL)
          SELECT DISTINCT nid,
                          unnest(ruleset_names) AS ruleset_name
          FROM ra) q;
END;
$f$;


CREATE OR REPLACE FUNCTION effective_access_rulesets_read_type(node_id integer, _ruletype text)
    RETURNS SETOF node_to_access_ruleset
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
IF EXISTS (SELECT * FROM node_to_access_ruleset WHERE nid=node_id AND ruletype=_ruletype) THEN
    RETURN QUERY SELECT * FROM node_to_access_ruleset WHERE nid=node_id AND ruletype=_ruletype;
END IF;
RETURN QUERY SELECT * FROM inherited_access_rulesets_read_type(node_id, _ruletype);
END;
$f$;


CREATE OR REPLACE FUNCTION inherited_access_rulesets_write_type(node_id integer, _ruletype text)
    RETURNS SETOF node_to_access_ruleset
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY
    SELECT DISTINCT node_id AS nid,
                    na.ruleset_name,
                    _ruletype AS ruletype,
                    na.invert,
                    na.blocking,
                    na.private
    FROM noderelation nr
    JOIN node_to_access_ruleset na ON nr.nid=na.nid
    WHERE cid=node_id
      AND ruletype = _ruletype;
END;
$f$;


CREATE OR REPLACE FUNCTION effective_access_rulesets_write_type(node_id integer, _ruletype text)
    RETURNS SETOF node_to_access_ruleset
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY
    SELECT * FROM inherited_access_rulesets_write_type(node_id, _ruletype)
    UNION
    SELECT * FROM node_to_access_ruleset WHERE nid=node_id AND ruletype=_ruletype;
END;
$f$;


CREATE OR REPLACE FUNCTION inherited_access_rulesets(node_id integer)
    RETURNS SETOF node_to_access_ruleset
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY 
    SELECT * FROM inherited_access_rulesets_read_type(node_id, 'read')
UNION ALL 
    SELECT * FROM inherited_access_rulesets_write_type(node_id, 'write')
UNION ALL
    SELECT * FROM inherited_access_rulesets_read_type(node_id, 'data')
;
END;
$f$;


CREATE OR REPLACE FUNCTION effective_access_rulesets(node_id integer)
    RETURNS SETOF node_to_access_ruleset
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN QUERY 
    SELECT * FROM effective_access_rulesets_read_type(node_id, 'read')
UNION ALL 
    SELECT * FROM effective_access_rulesets_write_type(node_id, 'write')
UNION ALL
    SELECT * FROM effective_access_rulesets_read_type(node_id, 'data')
;
END;
$f$;


--- rules from rulesets
CREATE OR REPLACE FUNCTION create_node_rulemappings_from_rulesets(_ruletype text)
    RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    INSERT INTO node_to_access_rule
    SELECT DISTINCT nid,
           rule_id, 
           _ruletype,
           arr.invert != nar.invert AS invert,
           false as inherited, 
           arr.blocking OR nar.blocking AS blocking
    FROM access_ruleset_to_rule arr
    JOIN node_to_access_ruleset nar ON arr.ruleset_name=nar.ruleset_name
    WHERE nar.ruletype=_ruletype
    ON CONFLICT DO NOTHING;
END;
$f$;


--- trigger functions for access rules

CREATE OR REPLACE FUNCTION on_node_to_access_ruleset_insert()
    RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    IF NEW.ruletype in ('read', 'data') THEN
        -- clear inherited rules first for read-type rules
        DELETE FROM node_to_access_rule 
        WHERE nid=NEW.nid 
        AND ruletype=NEW.ruletype 
        AND inherited=true;
    END IF;

    INSERT INTO node_to_access_rule
    SELECT NEW.nid AS nid,
           rule_id, 
           NEW.ruletype AS ruletype,
           invert != NEW.invert AS invert,
           false as inherited, 
           blocking OR NEW.blocking AS blocking
    FROM access_ruleset_to_rule 
    WHERE ruleset_name=NEW.ruleset_name
    ON CONFLICT DO NOTHING;
    
RETURN NEW;
END;
$f$;


CREATE OR REPLACE FUNCTION on_node_to_access_ruleset_delete()
    RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
BEGIN
    DELETE FROM node_to_access_rule
    WHERE nid=OLD.nid
    AND ruletype=OLD.ruletype
    AND (nid, rule_id, ruletype, invert, false, blocking) 
        NOT IN (SELECT na.nid, arr.rule_id, na.ruletype, na.invert != arr.invert, false, na.blocking OR arr.blocking
                    FROM access_ruleset_to_rule arr
                    JOIN node_to_access_ruleset na ON arr.ruleset_name=na.ruleset_name
                    WHERE na.nid=OLD.nid);

    IF OLD.ruletype IN ('read', 'data') 
        AND NOT EXISTS (SELECT FROM node_to_access_ruleset WHERE nid=OLD.nid AND ruletype=OLD.ruletype)
        AND NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=OLD.nid AND ruletype=OLD.ruletype) THEN
        -- inherit from parents if no rules and rulesets are present for the node anymore
        INSERT INTO node_to_access_rule SELECT * FROM _inherited_access_rules_read_type(OLD.nid, OLD.ruletype);
    END IF;
RETURN OLD;
END;
$f$;


-- XXX: "cheap" solution: just remove the access ruleset and add it again. 
-- XXX: No problem for special rulesets, but should be replaced by more intelligent code when we have a Access Rule Editor
CREATE OR REPLACE FUNCTION on_access_ruleset_to_rule_insert_delete()
    RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
DECLARE
    rec access_ruleset_to_rule;
BEGIN

IF TG_OP = 'INSERT' THEN
    rec = NEW;
ELSE
    rec = OLD;
END IF;

WITH del AS (DELETE FROM node_to_access_ruleset nar 
             WHERE nar.ruleset_name=rec.ruleset_name 
             RETURNING *)

INSERT INTO node_to_access_ruleset 
SELECT del.nid AS nid,
       rec.ruleset_name AS ruleset_name,
       del.ruletype AS ruletype,
       del.invert AS invert,
       del.blocking AS blocking,
       del.private AS private
FROM del;

RETURN rec;
END;
$f$;


CREATE OR REPLACE FUNCTION on_access_ruleset_to_rule_delete_delete_empty_private_rulesets()
    RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO :search_path
    VOLATILE
AS $f$
DECLARE
    nid integer;
BEGIN
    -- find out if the ruleset is a private ruleset for a node
    nid = (SELECT nar.nid FROM node_to_access_ruleset nar WHERE private = true and ruleset_name = old.ruleset_name);

    IF (nid > 0) THEN
        -- is it an empty ruleset? Then delete it.
        IF NOT EXISTS (SELECT FROM access_ruleset_to_rule WHERE ruleset_name = old.ruleset_name) THEN
            DELETE FROM node_to_access_ruleset WHERE ruleset_name = old.ruleset_name;
            DELETE FROM access_ruleset WHERE name = old.ruleset_name;
        END IF;
    END IF;

RETURN old;
END;
$f$;


----
-- maintenance functions
----

CREATE TYPE rule_duplication AS (surviving_rule_id integer, duplicates integer[]);

-- remove duplicate access rules with same content, but different id. Updates foreign keys in dependent tables.
CREATE OR REPLACE FUNCTION deduplicate_access_rules ()
   RETURNS SETOF rule_duplication
   LANGUAGE plpgsql
    SET search_path TO :search_path
   VOLATILE
AS
$f$
BEGIN
SET CONSTRAINTS ALL DEFERRED;
RETURN QUERY
    WITH dupes AS
      (SELECT rule_ids[1] AS surviving_rule_id,
                      rule_ids[2:cardinality(rule_ids)] AS duplicates
       FROM
         (SELECT array_agg(id ORDER BY id) AS rule_ids
          FROM access_rule
          GROUP BY invert_subnet, invert_date, invert_group, group_ids, subnets, dateranges
          HAVING count(*) > 1) r),

    deleted_dupes AS
      (DELETE
       FROM access_rule
       WHERE ARRAY[id] <@ ANY (SELECT duplicates FROM dupes)),
       
    updated_node_to_access_rule AS
        (UPDATE node_to_access_rule
        SET rule_id = dupes.surviving_rule_id
        FROM dupes
        WHERE ARRAY[rule_id] <@ dupes.duplicates),
        
    updated_access_ruleset_to_rule AS
        (UPDATE access_ruleset_to_rule
        SET rule_id = dupes.surviving_rule_id
        FROM dupes
        WHERE ARRAY[rule_id] <@ dupes.duplicates)

    SELECT * FROM dupes ORDER BY surviving_rule_id;
END;
$f$;


CREATE OR REPLACE FUNCTION find_duplicate_rules()
   RETURNS SETOF rule_duplication
   LANGUAGE plpgsql
   SET search_path TO :search_path
   STABLE
AS
$f$
BEGIN
RETURN QUERY
    SELECT rule_ids[1] AS surviving_rule_id,
           rule_ids[2:cardinality(rule_ids)] AS duplicates
    FROM
      (SELECT array_agg(id ORDER BY id) AS rule_ids,
              count(*)
       FROM access_rule
       GROUP BY invert_subnet,
                invert_date,
                invert_group,
                group_ids,
                subnets,
                dateranges HAVING count(*) > 1
       ORDER BY count(*) DESC) r ;
END;
$f$;


----
-- utility functions
----

CREATE OR REPLACE FUNCTION group_ids_to_names(group_ids integer[])
   RETURNS text[]
   LANGUAGE plpgsql
   SET search_path TO :search_path
   STABLE
AS
$f$
DECLARE 
    group_names text[];
BEGIN
    SELECT array_agg(( SELECT usergroup.name
                   FROM usergroup
                  WHERE usergroup.id = f.f)) AS a
           INTO group_names
           FROM unnest(group_ids) f
    ;
    
RETURN group_names;
END;
$f$;
