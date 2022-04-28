-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

-- predefined rules from the access table that are never used
 
 
SELECT name FROM mediatum_import.access 
EXCEPT 
(SELECT DISTINCT q.n 
   FROM (SELECT unnest (regexp_split_to_array (node.readaccess, ',')) AS n 
           FROM mediatum_import.node) q 
  WHERE n NOT LIKE '{%' 
 UNION ALL 
 SELECT DISTINCT q.n 
   FROM (SELECT unnest (regexp_split_to_array (node.writeaccess, ',')) AS n 
           FROM mediatum_import.node) q 
  WHERE n NOT LIKE '{%' 
 UNION ALL 
 SELECT DISTINCT q.n 
   FROM (SELECT unnest (regexp_split_to_array (node.dataaccess, ',')) AS n 
           FROM mediatum_import.node) q 
  WHERE n NOT LIKE '{%'); 
 
-- predefined rules used by nodes that are not defined in the access table 
 
SELECT DISTINCT q.n AS rulename 
  FROM (SELECT unnest (regexp_split_to_array (node.readaccess, ',')) AS n 
          FROM mediatum_import.node) q 
 WHERE     n NOT LIKE '{%' 
       AND NOT EXISTS 
              (SELECT rule 
                 FROM mediatum_import.access 
                WHERE name = q.n);
