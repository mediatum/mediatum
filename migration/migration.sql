CREATE OR REPLACE FUNCTION set_subnode_attribute()
   RETURNS void
   LANGUAGE plpgsql
    SET search_path TO :search_path
    AS
    $f$
BEGIN
    UPDATE node SET subnode = true
    WHERE id IN (SELECT n1.id
                 FROM node n1 JOIN nodemapping nm1 ON cid=n1.id JOIN node n2 ON nid=n2.id
                 WHERE n2.type IN (SELECT name FROM mediatum.nodetype WHERE is_container = false));

END;
$f$;


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

    UPDATE mediatum.node
    SET schema = type
    WHERE type IN (SELECT name FROM mediatum.nodetype WHERE is_container = true);

    UPDATE mediatum.node
    SET type = 'other'
    WHERE type = 'file';

    UPDATE mediatum.node
    SET schema = 'collection'
    WHERE type = 'collections';

    RAISE NOTICE 'migrated node';

    -- nodefile is a one-to-many relationship from node to file
    -- we migrate it to a many-to-many relationship

    INSERT INTO mediatum.file (path, filetype, mimetype)
    SELECT DISTINCT 
        filename AS path, 
        type AS filetype, 
        mimetype
    FROM mediatum_import.nodefile;

    CREATE INDEX file_mig ON mediatum.file (path, filetype, mimetype);

    INSERT INTO mediatum.node_to_file (nid, file_id)
    SELECT DISTINCT
        nid, 
        f.id AS file_id
    FROM mediatum_import.nodefile nf 
    JOIN file f ON (f.path=nf.filename and f.filetype=nf.type and f.mimetype=nf.mimetype);
    
    DROP INDEX file_mig;

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
    FROM(SELECT nid, json_object(array_agg(name), array_agg(value))::jsonb as attrjson
         FROM mediatum_import.nodeattribute
         WHERE name NOT LIKE 'system.%'
         GROUP BY nid) q
    WHERE q.nid = mediatum.node.id;

    -- old "system." attrs go to node.system_attrs without the prefix
    UPDATE mediatum.node
    SET system_attrs=attrjson
    FROM(SELECT nid, json_object(array_agg(substring(name, 8)), array_agg(value))::jsonb as attrjson
         FROM mediatum_import.nodeattribute
         WHERE name LIKE 'system.%'
         GROUP BY nid) q
    WHERE q.nid = mediatum.node.id;

    -- we want empty attrs objects for nodes without attributes. NULL doesn't make sense

    UPDATE mediatum.node SET attrs = '{}' where attrs is NULL;
    UPDATE mediatum.node SET system_attrs = '{}' where system_attrs is NULL;

    -- original type is 'users', we need 'externalusers' in postgres to distinguish it from the users node

    UPDATE mediatum.node SET type = 'externalusers' WHERE name = 'external_users';

    -- dashes are not allowed, use underscores

    UPDATE mediatum.node SET type = replace(type, '-', '_') WHERE type LIKE '%-%';

    -- some workflowsteps have types which do not correspond to the class names, rename them

    UPDATE mediatum.node SET type = 'workflowstep_editmetadata' WHERE type = 'workflowstep_edit';
    UPDATE mediatum.node SET type = 'workflowstep_sendemail' WHERE type = 'workflowstep_send_email';
    UPDATE mediatum.node SET type = 'workflowstep_urn' WHERE type = 'workflowstep_addurn';
    UPDATE mediatum.node SET type = 'workflowstep_buildinfid' WHERE type = 'workflowstep_buildInfId';
    UPDATE mediatum.node SET type = 'workflowstep_showdata' WHERE type = 'workflowstep_wait';
    UPDATE mediatum.node SET type = 'workflowstep_showdata' WHERE type = 'workflowstep_jahrbuch';

    -- scholar plugin

    UPDATE mediatum.node SET type = 'directoryscholar' WHERE type = 'directory_scholar';


    RAISE NOTICE 'data migration finished';

    INSERT INTO mediatum.noderelation SELECT DISTINCT * FROM mediatum.transitive_closure_without_direct_connections();

    RAISE NOTICE 'transitive node connections finished';

    PERFORM set_subnode_attribute();

    RAISE NOTICE 'subnode attribute set';

    INSERT INTO node_alias (alias, nid) SELECT system_attrs->>'aliascol' AS alias, id as nid FROM node WHERE system_attrs ? 'aliascol';

    RAISE NOTICE 'migrated node aliases';

    UPDATE node SET system_attrs = jsonb_object_delete_keys(system_attrs, 'aliascol') WHERE system_attrs ? 'aliascol';

    RAISE NOTICE 'deleted obsolete attributes';

    PERFORM setval('node_id_seq', (SELECT max(id) FROM node));

    RAISE NOTICE 'reset node id sequence to max node ID';
END;
$f$;


-- delete nodes that migrated to a different table. They have been renamed to migration_<type>.
CREATE OR REPLACE FUNCTION delete_migrated_nodes()
   RETURNS void
   LANGUAGE plpgsql
    SET search_path TO :search_path
       VOLATILE
    AS
    $f$
DECLARE
    deleted_nodes integer;
BEGIN
    SET CONSTRAINTS ALL DEFERRED;

    WITH deleted AS
        (DELETE FROM node WHERE type LIKE 'migration_%' RETURNING id),

    deleted_rel AS
        (DELETE FROM noderelation WHERE nid IN (SELECT id FROM deleted) OR cid IN (SELECT id FROM deleted))

    SELECT count(id) INTO deleted_nodes FROM deleted;

    RAISE NOTICE '% table-migrated nodes deleted', deleted_nodes;

END;
$f$;
