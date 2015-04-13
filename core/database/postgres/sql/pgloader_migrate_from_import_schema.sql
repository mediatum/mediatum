 
 


TRUNCATE mediatum.nodefile;
TRUNCATE mediatum.node CASCADE;
TRUNCATE mediatum.noderelation;


 
 

INSERT INTO mediatum.node 
SELECT id, split_part(type, '/', 1) as type, split_part(type, '/', 2) as schema, name, orderpos
FROM mediatum_import.node;

 
 

INSERT INTO mediatum.nodefile
SELECT DISTINCT nid, filename AS path, type AS filetype, mimetype
FROM mediatum_import.nodefile;

 
 

INSERT INTO mediatum.noderelation
SELECT DISTINCT nid, cid, 1
FROM mediatum_import.nodemapping;

 
 

 

UPDATE mediatum.node 
SET attrs=attrjson
FROM(SELECT nid, json_object(array_agg(name), array_agg(value))::jsonb as attrjson FROM mediatum_import.nodeattribute GROUP BY nid) q
WHERE q.nid = mediatum.node.id;

 

UPDATE mediatum.node SET type = 'externalusers' WHERE name = 'external_users';

 

UPDATE mediatum.node SET type = replace(type, '-', '_') WHERE type LIKE '%-%';

 

UPDATE mediatum.node SET type = 'workflowstep_editmetadata' WHERE type = 'workflowstep_edit';
UPDATE mediatum.node SET type = 'workflowstep_sendemail' WHERE type = 'workflowstep_send_email';
UPDATE mediatum.node SET type = 'workflowstep_urn' WHERE type = 'workflowstep_addurn';

 

INSERT INTO mediatum.noderelation SELECT DISTINCT * FROM mediatum.transitive_closure_without_direct_connections();
