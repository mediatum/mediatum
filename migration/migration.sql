CREATE OR REPLACE FUNCTION mediatum.migrate_core() RETURNS void
    LANGUAGE plpgsql
    SET search_path = mediatum
    AS $f$
BEGIN
    -- type in import has the form '<type>/<schema>', we must split it
    -- some fields missing, add later when ACL is implemented with postgres
    
    INSERT INTO mediatum.node 
    SELECT id, split_part(type, '/', 1) as type, split_part(type, '/', 2) as schema, name, orderpos
    FROM mediatum_import.node;
    
    RAISE NOTICE 'migrated node';
    
    INSERT INTO mediatum.nodefile
    SELECT DISTINCT nid, filename AS path, type AS filetype, mimetype
    FROM mediatum_import.nodefile;
    
    RAISE NOTICE 'migrated nodefile';
    
    INSERT INTO mediatum.noderelation
    SELECT DISTINCT nid, cid, 1
    FROM mediatum_import.nodemapping;
    
    RAISE NOTICE 'migrated nodemapping';
    
    PERFORM mediatum.purge_nodes();
    
    RAISE NOTICE 'purged unreachable nodes';
    
    -- migrate imported nodeattribute table to node.attrs
    
    
    UPDATE mediatum.node 
    SET attrs=attrjson
    FROM(SELECT nid, json_object(array_agg(name), array_agg(value))::jsonb as attrjson FROM mediatum_import.nodeattribute GROUP BY nid) q
    WHERE q.nid = mediatum.node.id;
    
    -- we want empty attrs objects for nodes without attributes. NULL doesn't make sense  
    
    UPDATE mediatum.node SET attrs = '{}' where attrs is NULL;
    
    -- original type is 'users', we need 'externalusers' in postgres to distinguish it from the users node
    
    UPDATE mediatum.node SET type = 'externalusers' WHERE name = 'external_users';
    
    -- dashes are not allowed, use underscores
    
    UPDATE mediatum.node SET type = replace(type, '-', '_') WHERE type LIKE '%-%';
    
    -- some workflowsteps have types which do not correspond to the class names, rename them
    
    UPDATE mediatum.node SET type = 'workflowstep_editmetadata' WHERE type = 'workflowstep_edit';
    UPDATE mediatum.node SET type = 'workflowstep_sendemail' WHERE type = 'workflowstep_send_email';
    UPDATE mediatum.node SET type = 'workflowstep_urn' WHERE type = 'workflowstep_addurn';
    
    RAISE NOTICE 'data migration finished';
    
    INSERT INTO mediatum.noderelation SELECT DISTINCT * FROM mediatum.transitive_closure_without_direct_connections();
    
    RAISE NOTICE 'transitive node connections finished';
END;
$f$;
