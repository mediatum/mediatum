-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

                                        (SELECT nm.nid,
                                           (SELECT array_agg(rule_id) AS rule_ids
                                            FROM nodemapping nm
                                            JOIN node_to_access_rule na ON nm.nid=na.nid
                                            WHERE cid=:id
                                              AND ruletype='read')
                                        
                                        FROM nodemapping nm
                                         WHERE cid = :id
                                           AND NOT EXISTS
                                             (SELECT
                                              FROM node_to_access_rule na1
                                              WHERE na1.nid=nm.nid
                                                AND ruletype='read')
                                         UNION ALL SELECT 0,
                                           (SELECT array_agg(rule_id) AS rule_ids
                                            FROM nodemapping nm
                                            JOIN node_to_access_rule na ON nm.nid=na.nid
                                            WHERE cid=:id
                                            AND ruletype='read'));

 WITH RECURSIVE ra(nid, rule_ids) AS (
                                        (SELECT nm.nid,
                                           (SELECT array_agg(rule_id) AS rule_ids
                                            FROM nodemapping nm
                                            JOIN node_to_access_rule na ON nm.nid=na.nid
                                            WHERE cid=:id
                                              AND ruletype='read')FROM nodemapping nm
                                         WHERE cid = :id
                                           AND NOT EXISTS
                                             (SELECT
                                              FROM node_to_access_rule na1
                                              WHERE na1.nid=nm.nid
                                                AND ruletype='read')
                                         UNION ALL SELECT 0,
                                           (SELECT array_agg(rule_id) AS rule_ids
                                            FROM nodemapping nm
                                            JOIN node_to_access_rule na ON nm.nid=na.nid
                                            WHERE cid=:id
                                              AND ruletype='read'))
                                      UNION ALL
                                        (SELECT nm.nid, ra.rule_ids || 
                                           (SELECT array_agg(rule_id) AS rule_ids
                                            FROM nodemapping nm
                                            JOIN node_to_access_rule na ON nm.nid=na.nid
                                            WHERE cid=nm.nid
                                              AND ruletype='read')

                                         FROM nodemapping nm,ra
                                         WHERE cid = ra.nid
                                           AND NOT EXISTS
                                             (SELECT
                                              FROM node_to_access_rule na1
                                              WHERE na1.nid=nm.nid
                                            AND ruletype='read')))

SELECT *
FROM ra;

