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
WHERE user_id is not NULL ORDER BY usergroup_id
;

;
