-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

SELECT substring(n1.name
                 FROM 20) AS dir,
       n2.id,
       substring(n2.name
                 FOR 20) AS name,
       n2.type
FROM node n1
JOIN noderelation ON id=nid
JOIN node n2 ON cid=n2.id
WHERE n1.name LIKE 'Arbeitsverzeichnis (%'
  AND n2.name NOT IN ('Papierkorb',
                      'Inkonsistente Daten',
                      'Uploads',
                      'Importe') ;
