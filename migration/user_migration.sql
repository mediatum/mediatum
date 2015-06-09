-- Creates usergroup entries from imported group nodes
CREATE OR REPLACE FUNCTION mediatum_import.migrate_usergroups() RETURNS void
    LANGUAGE plpgsql
    SET search_path = mediatum_import
    AS $f$
BEGIN
    INSERT INTO mediatum.usergroup (id, name, description, hidden_edit_functions, is_workflow_editor_group, is_editor_group)
    SELECT id, 
    trim(' ' from name), 
    trim(' ' from attrs->>'description') AS description,
    regexp_split_to_array(attrs->>'hideedit', ';') AS hidden_edit_functions,
    bool(position('w' in attrs->>'opts')) AS is_workflow_editor_group,
    bool(position('e' in attrs->>'opts')) AS is_editor_group
    FROM node 
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'usergroups'));
END;
$f$;


-- Creates user entries from imported internal user nodes
CREATE OR REPLACE FUNCTION mediatum_import.migrate_internal_users() RETURNS void
    LANGUAGE plpgsql
    SET search_path = mediatum_import
    AS $f$
BEGIN
    INSERT INTO mediatum.authenticator (id, auth_type, name)
         VALUES (0, 'internal', 'default');
    
    INSERT INTO mediatum.user (id, login_name, display_name, firstname, lastname, telephone, email, organisation, password_hash, comment, can_change_password, can_edit_shoppingbag, authenticator_id) 
    SELECT id,
    name AS login_name,
    trim(' ' from attrs->>'lastname') || ' ' || trim(' ' from attrs->>'firstname') AS display_name,
    trim(' ' from attrs->>'firstname') AS firstname,
    trim(' ' from attrs->>'lastname') AS lastname,
    trim(' ' from attrs->>'telephone') AS telephone,
    trim(' ' from attrs->>'email') AS email,
    trim(' ' from attrs->>'organisation') AS organisation,
    trim(' ' from attrs->>'password') AS password_hash,
    trim(' ' from attrs->>'comment') AS comment,
    bool(position('c' in attrs->>'opts')) AS can_change_password,
    bool(position('s' in attrs->>'opts')) AS can_edit_shoppingbag,
    0 as authenticator_id
    FROM node 
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'users'));
    
    -- find home dirs by name
    -- XXX: LIMIT 1 hack for duplicate home directories
    -- (warning: home dir association must be unique or this will fail!)
    
    UPDATE mediatum.user u
    SET home_dir_id = (SELECT n.id 
                FROM mediatum_import.node AS n WHERE n.name LIKE 'Arbeitsverzeichnis (%' AND n.readaccess = '{user ' || u.display_name || '}' LIMIT 1)
        WHERE authenticator_id = 0;
    
    
    INSERT INTO mediatum.user_to_usergroup
       SELECT cid AS user_id, id AS usergroup_id
         FROM nodemapping JOIN node ON nid = id
        WHERE     node.id IN (SELECT cid
                                FROM nodemapping
                               WHERE nid = (SELECT id
                                              FROM node
                                             WHERE type = 'usergroups'))
              AND cid NOT IN
                     (SELECT cid
                        FROM nodemapping
                       WHERE nid =
                                (SELECT id
                                   FROM node
                                  WHERE     type = 'directory'
                                        AND name = 'yearbookuser')) -- ignore yearbookuser
              AND cid NOT IN (SELECT cid
                                FROM nodemapping
                               WHERE nid = 674265) -- user from Jahrbuch-User group ignored
    ;
END;
$f$;

    
-- Creates user entries from imported home directories for dynamic users (mediatum-dynauth plugin)
CREATE OR REPLACE FUNCTION mediatum_import.migrate_ads_users() RETURNS void
    LANGUAGE plpgsql
    SET search_path = mediatum_import
    AS $f$
BEGIN
    INSERT INTO authenticator (id, name, auth_type) VALUES (1, 'ads', 'dynauth');
    
    -- select info from home dirs for ads user (has system.name.adsuser attribute) and create user from it
    
    INSERT INTO mediatum.user (display_name, comment, home_dir_id, authenticator_id)
    SELECT
    trim(' ' from attrs->>'system.name.adsuser') AS display_name,
    'migration: created from home dir' AS comment,
    node.id AS home_dir_id,
    1 as authenticator_id
    FROM node 
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'home')) 
    AND attrs ? 'system.dirid.adsuser'
    ;
    -- additional user info from home dir
    
    INSERT INTO dynauth.user_info (name, user_type, dirid, dirgroups, user_id) 
    SELECT
    trim(' ' from attrs->>'system.name.adsuser') AS name,
    'adsuser'::text as user_type,
    trim(' ' from attrs->>'system.dirid.adsuser') AS dirid,
    (SELECT regexp_split_to_array(attrs->>'system.dirgroups.adsuser', '\|#\|')) AS dirgroups,
    (SELECT u.id from mediatum.user as u WHERE display_name = trim(' ' from node.attrs->>'system.name.adsuser') LIMIT 1) AS user_id
    FROM node 
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'home')) 
    AND attrs ? 'system.dirid.adsuser'
    ;
    
    -- group membership is determined by the dynamic_users attr of groups that contains a newline-separated login name list
    
    INSERT INTO mediatum.user_to_usergroup (usergroup_id, user_id)
    SELECT usergroup_id, user_id FROM 
        (SELECT id as usergroup_id, 
            (SELECT user_id FROM dynauth.user_info WHERE dynauth.user_info.dirid = q.dirid LIMIT 1) as user_id
        FROM 
            (SELECT distinct id, 
            unnest(array_remove(regexp_split_to_array(attrs->>'dynamic_users', '\r\n'), '')) as dirid
            FROM node WHERE attrs ? 'dynamic_users'
            ) q
        ) s
    WHERE user_id is not NULL ORDER BY usergroup_id;
END;
$f$;

