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


-- functions that determine if the current user (in groups `group_ids`) from ipaddr has access to `node_id` on the given date

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
    STABLE
AS $f$
BEGIN
    RETURN _has_read_type_access_to_node(node_id, 'data', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION _has_write_type_access_to_node(node_id integer, _ruletype text, _group_ids integer[], ipaddr inet, _date date) 
    RETURNS boolean
    LANGUAGE plpgsql
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
    STABLE
AS $f$
BEGIN
    RETURN _has_write_type_access_to_node(node_id, 'write', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION experiment_read_accessible_nodes(_group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL, lim integer = null, off integer= null) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
RETURN QUERY
    SELECT node.* FROM node
    WHERE has_read_access_to_node(node.id, _group_ids, ipaddr, _date)
    LIMIT lim
    OFFSET off;
END;
$f$;


CREATE OR REPLACE FUNCTION _read_type_accessible_nodes(_ruletype text, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL, lim integer = null)
    RETURNS SETOF node
    LANGUAGE plpgsql
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


CREATE OR REPLACE FUNCTION read_accessible_nodes(_group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL, lim integer = null) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
    RETURN QUERY SELECT * FROM _read_type_accessible_nodes('read', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION data_accessible_nodes(_group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS SETOF node
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
    RETURN QUERY SELECT * FROM _read_type_accessible_nodes('data', _group_ids, ipaddr, _date);
END;
$f$;


CREATE OR REPLACE FUNCTION _write_type_accessible_nodes(_ruletype text, _group_ids integer[] = NULL, ipaddr inet = NULL, _date date = NULL) 
    RETURNS SETOF node
    LANGUAGE plpgsql
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
    STABLE
AS $f$
BEGIN
    RETURN QUERY SELECT * FROM _write_type_accessible_nodes('write', _group_ids, ipaddr, _date);
END;
$f$;


-- update functions

-- blocking is not supported for read-type access rules, so the blocking attribute is always returned as NULL
CREATE OR REPLACE FUNCTION _inherited_access_mappings_read_type(node_id integer, _ruletype text) 
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
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


CREATE OR REPLACE FUNCTION inherited_access_mappings_read(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
RETURN QUERY SELECT * FROM _inherited_access_mappings_read_type(node_id, 'read');
END;
$f$;


CREATE OR REPLACE FUNCTION create_all_inherited_access_mappings_read()
    RETURNS void
    LANGUAGE plpgsql
AS $f$
BEGIN
    INSERT INTO node_to_access_rule 
    SELECT i.* FROM node 
    JOIN LATERAL inherited_access_mappings_read(node.id) i ON TRUE 
    WHERE node.id NOT IN (SELECT nid FROM node_to_access_rule WHERE ruletype='read');
END;
$f$;


CREATE OR REPLACE FUNCTION create_all_inherited_access_mappings_data()
    RETURNS void
    LANGUAGE plpgsql
AS $f$
BEGIN
    INSERT INTO node_to_access_rule 
    SELECT i.* FROM node 
    JOIN LATERAL inherited_access_mappings_data(node.id) i ON TRUE 
    WHERE node.id NOT IN (SELECT nid FROM node_to_access_rule WHERE ruletype='data');
END;
$f$;



CREATE OR REPLACE FUNCTION inherited_access_mappings_data(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
RETURN QUERY SELECT * FROM _inherited_access_mappings_read_type(node_id, 'data');
END;
$f$;


CREATE OR REPLACE FUNCTION inherited_access_mappings_write(node_id integer)
    RETURNS SETOF node_to_access_rule
    LANGUAGE plpgsql
    STABLE
AS $f$
BEGIN
RETURN QUERY
    SELECT DISTINCT node_id AS nid,
                    na.rule_id,
                    'write' AS ruletype,
                    na.invert,
                    na.blocking,
                    TRUE AS inherited
    FROM noderelation nr
    JOIN node_to_access_rule na ON nr.nid=na.nid
    WHERE cid=node_id
      AND ruletype = 'write';
END;
$f$;


CREATE OR REPLACE FUNCTION create_all_inherited_access_mappings_write()
    RETURNS void
    LANGUAGE plpgsql
AS $f$
BEGIN
    -- XXX: very strange: this fails when trying to insert directy into the node_to_access table
    -- this solution with a temp table works

    CREATE TEMPORARY TABLE temp_create_all_inherited_access_mappings_write AS
    SELECT i.* FROM node 
    JOIN LATERAL inherited_access_mappings_write(node.id) i ON TRUE 
    WHERE node.id NOT IN (SELECT nid FROM node_to_access_rule WHERE ruletype='write');

    INSERT INTO node_to_access_rule 
    SELECT * FROM temp_create_all_inherited_access_mappings_write;
END;
$f$;


