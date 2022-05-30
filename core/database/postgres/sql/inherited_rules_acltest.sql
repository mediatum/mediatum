-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

SELECT :id AS nid, rule_id, 'read' AS ruletype,
  (SELECT invert
   FROM node_to_access_rule na
   WHERE na.nid=q.nid
     AND na.rule_id=q.rule_id
     AND ruletype='read'), TRUE AS inherited
FROM (WITH RECURSIVE ra(nid, rule_ids) AS
        (SELECT nm.nid,
           (SELECT array_agg(rule_id) AS rule_ids
            FROM node_to_access_rule n
            WHERE nid=nm.nid
              AND ruletype='read')
         FROM nodemapping nm
         WHERE nm.cid = :id
         UNION ALL SELECT nm.nid,
           (SELECT array_agg(rule_id) AS rule_ids
            FROM node_to_access_rule n
            WHERE nid=nm.nid
              AND ruletype='read')
         FROM nodemapping nm,
                          ra
         WHERE nm.cid = ra.nid
           AND ra.rule_ids IS NULL)
      SELECT DISTINCT nid,
                      unnest(rule_ids) AS rule_id
      FROM ra) q ;


SELECT DISTINCT :id AS nid,
                na.rule_id,
                'write' AS ruletype,
                na.invert,
                TRUE AS inherited
FROM noderelation nr
JOIN node_to_access_rule na ON nr.nid=na.nid
WHERE cid=:id
  AND ruletype = 'write' ;

