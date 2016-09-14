-- Creates usergroup entries from imported group nodes
CREATE OR REPLACE FUNCTION mediatum.migrate_usergroups() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS $f$
BEGIN
    INSERT INTO usergroup (id, name, description, hidden_edit_functions, is_workflow_editor_group, is_editor_group, created_at)
    SELECT id,
    trim(' ' from name),
    trim(' ' from attrs->>'description') AS description,
    coalesce(regexp_split_to_array(attrs->>'hideedit', ';'), '{}') AS hidden_edit_functions,
    bool(position('w' in attrs->>'opts')) AS is_workflow_editor_group,
    bool(position('e' in attrs->>'opts')) AS is_editor_group,
    now() AS created_at
    FROM node
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'usergroups' AND type = 'usergroups'))
    ORDER BY id;
END;
$f$;


-- Creates user entries from imported internal user nodes
CREATE OR REPLACE FUNCTION mediatum.migrate_internal_users() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS $f$

DECLARE 
    rows integer;
    internal_authenticator_id integer;
BEGIN
    INSERT INTO authenticator (auth_type, name)
         VALUES ('internal', 'default') RETURNING id INTO internal_authenticator_id;

    INSERT INTO mediatum.user (id, login_name, display_name, firstname, lastname, telephone, email,
        organisation, password_hash, comment, can_change_password, can_edit_shoppingbag, authenticator_id, created_at)
    SELECT id,
    name AS login_name,
    nullif(trim(' ' from attrs->>'lastname') || ' ' || trim(' ' from attrs->>'firstname'), ' ') AS display_name,
    trim(' ' from attrs->>'firstname') AS firstname,
    trim(' ' from attrs->>'lastname') AS lastname,
    trim(' ' from attrs->>'telephone') AS telephone,
    trim(' ' from attrs->>'email') AS email,
    trim(' ' from attrs->>'organisation') AS organisation,
    trim(' ' from attrs->>'password') AS password_hash,
    trim(' ' from attrs->>'comment') AS comment,
    bool(position('c' in attrs->>'opts')) AS can_change_password,
    bool(position('s' in attrs->>'opts')) AS can_edit_shoppingbag,
    internal_authenticator_id AS authenticator_id,
    now() AS created_at
    FROM node
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'users' AND type = 'users'))
    ORDER BY id;

    GET DIAGNOSTICS rows = ROW_COUNT;
    RAISE NOTICE '% internal users inserted', rows;

    -- find home dirs by name
    -- warning: home dir association must be unique or this will fail!

    UPDATE mediatum.user u
    SET home_dir_id = (SELECT n.id
                FROM mediatum_import.node AS n
                WHERE n.id IN (SELECT cid FROM mediatum_import.nodemapping WHERE nid = (SELECT id FROM mediatum_import.node WHERE type = 'home'))
                AND n.readaccess = '{user ' || u.login_name || '}'
                -- check if home dir is actually present, could be unreachable in mediatum_import.node
                AND n.id IN (SELECT id FROM mediatum.node)
                ORDER BY id
                LIMIT 1 -- mediaTUM selects the home dir with the lowest ID if there are multiple choices (which should not happen...)
                )
        WHERE authenticator_id = internal_authenticator_id;

    RAISE NOTICE 'home dirs set, % users with home dir', (SELECT COUNT(*) FROM mediatum.user WHERE home_dir_id IS NOT NULL);

    INSERT INTO user_to_usergroup
    SELECT cid AS user_id, id AS usergroup_id
    FROM nodemapping JOIN node ON nid = id
    WHERE node.id IN (SELECT cid
                      FROM nodemapping
                      WHERE nid = (SELECT id FROM node WHERE type = 'usergroups'))
    -- ignore yearbookuser
    AND cid NOT IN (SELECT cid
                    FROM nodemapping
                    WHERE nid = (SELECT id FROM node WHERE type = 'directory' AND name = 'yearbookuser'));

    GET DIAGNOSTICS rows = ROW_COUNT;
    RAISE NOTICE 'users mapped to groups, % mappings', rows;

    PERFORM mediatum.reset_user_ids();

END;
$f$;


-- Creates user entries from imported home directories for dynamic users (former mediatum-dynauth plugin, now core.ldapauth)
CREATE OR REPLACE FUNCTION mediatum.migrate_dynauth_users() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS $f$
DECLARE
    rows integer;
    ads_authenticator_id integer;
BEGIN
    INSERT INTO authenticator (name, auth_type) VALUES ('ads', 'ldap') RETURNING id INTO ads_authenticator_id;

    -- select info from home dirs for ads user (has name.adsuser system attribute) and create user from it

    INSERT INTO mediatum.user (display_name, login_name, comment, last_login, home_dir_id, authenticator_id, created_at)
    SELECT
    trim(' ' from system_attrs->>'name.adsuser') AS display_name,
    trim(' ' from system_attrs->>'dirid.adsuser') AS login_name,
    'migration: created from home dir' AS comment,
    (system_attrs->>'last_authentication.adsuser')::timestamp AS last_login,
    node.id AS home_dir_id,
    ads_authenticator_id AS authenticator_id,
    coalesce((system_attrs->>'last_authentication.adsuser')::timestamp, now()) AS created_at -- no really the creation date, but better than nothing
    FROM node
    WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'home'))
    AND system_attrs ? 'dirid.adsuser'
    ;

    GET DIAGNOSTICS rows = ROW_COUNT;
    RAISE NOTICE '% dynauth users created from their home dirs', rows;

    -- Handle dynamic_users attr of groups. That attribute contains a newline-separated login name list.

    -- create placeholder users for dynamic_users login names not found in the user table
    INSERT INTO mediatum.user (login_name, comment, authenticator_id, created_at)
    SELECT
    q.login_name as login_name,
    'migration: created from dynuser list of group ' || array_to_string(group_name, ','),
    ads_authenticator_id AS authenticator_id,
    now() AS created_at
    FROM
        (SELECT distinct unnest(array_remove(regexp_split_to_array(attrs->>'dynamic_users', '\r\n'), '')) as login_name,
        array_agg(name) as group_name
        FROM mediatum.node WHERE type = 'usergroup' AND attrs ? 'dynamic_users'
        GROUP BY login_name
        ) q
    WHERE q.login_name NOT IN (SELECT login_name FROM mediatum.user WHERE login_name IS NOT NULL AND authenticator_id = ads_authenticator_id);

    GET DIAGNOSTICS rows = ROW_COUNT;
    RAISE NOTICE '% users created from dynamic user lists', rows;

    -- insert user-group relationships

    INSERT INTO user_to_usergroup (usergroup_id, user_id)
    SELECT usergroup_id, user_id FROM
        (SELECT id as usergroup_id,
            (SELECT id FROM mediatum.user WHERE mediatum.user.login_name = q.login_name AND authenticator_id = ads_authenticator_id LIMIT 1) as user_id
        FROM
            (SELECT distinct id,
            unnest(array_remove(regexp_split_to_array(attrs->>'dynamic_users', '\r\n'), '')) as login_name
            FROM node WHERE type = 'usergroup' AND attrs ? 'dynamic_users'
            ) q
        ) s
    ORDER BY usergroup_id;

    GET DIAGNOSTICS rows = ROW_COUNT;
    RAISE NOTICE '% user-group mappings for dynamic users', rows;

END;
$f$;


-- assign new IDs to users from the ID sequence
CREATE OR REPLACE FUNCTION reset_user_ids() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS
    $f$
BEGIN
    WITH mapping AS (SELECT id AS old, nextval('user_id_seq') AS new from mediatum.user),
        u1 AS (UPDATE mediatum.user_to_usergroup SET user_id=(SELECT new from mapping WHERE old=user_id))

    UPDATE mediatum.user SET id=(SELECT new from mapping WHERE old=id);
END;
$f$;


-- assign new IDs to user groups from the ID sequence
CREATE OR REPLACE FUNCTION reset_usergroup_ids() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS
    $f$
BEGIN
    WITH mapping AS (SELECT id AS old, nextval('usergroup_id_seq') AS new from usergroup),
            u1 AS (UPDATE mediatum.user_to_usergroup SET usergroup_id=(SELECT new from mapping WHERE old=usergroup_id))
    UPDATE mediatum.usergroup SET id=(SELECT new from mapping WHERE old=id) ;
END;
$f$;


CREATE OR REPLACE FUNCTION rename_user_system_nodes() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS
    $f$
BEGIN
    UPDATE node set type = 'migration_' || type
    WHERE type IN ('user', 'users', 'usergroup', 'usergroups', 'externalusers');
END;
$f$;


CREATE OR REPLACE FUNCTION clean_trash_dirs() RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    num_deleted_nodes integer;
BEGIN
    DELETE FROM noderelation WHERE nid IN
        (SELECT id
        FROM node JOIN noderelation ON id=cid
        WHERE distance = 2
        AND nid=(SELECT id from node WHERE type = 'home')
        AND name = 'Papierkorb');

    GET DIAGNOSTICS num_deleted_nodes = ROW_COUNT;
    RETURN num_deleted_nodes;
END;
$f$;


CREATE OR REPLACE FUNCTION delete_empty_special_dirs() RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    special_dir_ids integer[];
    deleted_special_dirs integer;
BEGIN
    SELECT array_agg(id)
    INTO special_dir_ids
    FROM node n JOIN noderelation nr ON id=cid
    WHERE distance = 2
    AND nid=(SELECT id from node WHERE type = 'home')
    AND n.name in ('Papierkorb',
                   'Inkonsistente Daten',
                   'Uploads',
                   'Importe')
    AND id NOT IN (SELECT nid FROM nodemapping);

    deleted_special_dirs = delete_nodes(special_dir_ids);
    RETURN deleted_special_dirs;
END;
$f$;


CREATE OR REPLACE FUNCTION purge_empty_home_dirs() RETURNS integer
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $f$
DECLARE
    home_dir_ids integer[];
    deleted_home_dirs integer;
BEGIN
    SELECT array_agg(id)
    INTO home_dir_ids
    FROM node JOIN nodemapping ON id=cid
    AND nid=(SELECT id from node WHERE type = 'home')
    AND name LIKE 'Arbeitsverzeichnis (%'
    AND id NOT IN (SELECT nid FROM nodemapping);

    UPDATE mediatum.user
    SET home_dir_id=NULL
    WHERE home_dir_id IN (SELECT unnest(home_dir_ids));

    deleted_home_dirs = delete_nodes(home_dir_ids);
    RETURN deleted_home_dirs;
END;
$f$;

