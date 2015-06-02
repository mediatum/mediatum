CREATE OR REPLACE FUNCTION check_access_rule(rule access_rule, _group_ids integer[], ipaddr inet, _date date) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
    STABLE
AS $f$
BEGIN
RETURN 
    (rule.subnets IS NULL OR ipaddr IS NULL OR (rule.invert_subnet # (ipaddr <<= ANY(rule.subnets))))
    AND (rule.group_ids IS NULL OR _group_ids IS NULL OR (rule.invert_group # (_group_ids && rule.group_ids)))
    AND (rule.dateranges IS NULL OR _date IS NULL OR (rule.invert_date # (_date <@ ANY(rule.dateranges))));
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
    AND na.invert # check_access_rule(a, _group_ids, ipaddr, _date));
END;
$f$;


CREATE OR REPLACE FUNCTION has_read_access_to_node(node_id integer, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS boolean
    LANGUAGE plpgsql
    SET search_path TO :search_path
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
    AND na.invert # check_access_rule(a, _group_ids, ipaddr, _date)

    EXCEPT

    SELECT node.id FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.blocking = true
    AND node.id = node_id
    AND NOT na.invert # check_access_rule(a, _group_ids, ipaddr, _date));

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
    AND na.invert # check_access_rule(a, _group_ids, ipaddr, _date);
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
    AND na.invert # check_access_rule(a, _group_ids, ipaddr, _date)

    EXCEPT

    SELECT node.* FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype=_ruletype
    AND na.blocking = true
    AND NOT na.invert # check_access_rule(a, _group_ids, ipaddr, _date);
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
IF EXISTS (SELECT FROM node_to_access_rule WHERE nid=node_id AND inherited = false) THEN
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
    RETURNING *;
END;
$f$;


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

