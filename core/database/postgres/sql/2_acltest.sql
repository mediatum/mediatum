-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

WITH RECURSIVE rootaccess(nid) AS
    (SELECT nm.cid as nid
    FROM nodemapping nm
    WHERE nm.nid = 1
    AND NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=nm.cid AND ruletype='read' AND inherited = false)

    UNION ALL

    SELECT nm.cid
    FROM nodemapping nm JOIN rootaccess ON nm.nid=rootaccess.nid
    AND NOT EXISTS (SELECT FROM node_to_access_rule WHERE nid=nm.cid AND ruletype='read' AND inherited = false)
)

SELECT DISTINCT nid,localread FROM rootaccess join lateral (select localread from mediatum_import.node where nid=id) i on true;
