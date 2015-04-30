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
-- warning: home dir association must be unique or this will fail!


UPDATE mediatum.user u
SET home_dir_id = (SELECT n.id 
            FROM mediatum_import.node AS n WHERE n.name LIKE 'Arbeitsverzeichnis (%' AND n.readaccess = ('{user ' || u.display_name || '}'))
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
