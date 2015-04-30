INSERT INTO mediatum.usergroup (id, name, description, hidden_edit_functions, is_workflow_editor_group, is_editor_group)
SELECT id, 
trim(' ' from name), 
trim(' ' from attrs->>'description') AS description,
regexp_split_to_array(attrs->>'hideedit', ';') AS hidden_edit_functions,
bool(position('w' in attrs->>'opts')) AS is_workflow_editor_group,
bool(position('e' in attrs->>'opts')) AS is_editor_group
FROM node 
WHERE id IN (SELECT cid FROM nodemapping WHERE nid=(SELECT id FROM node WHERE name = 'usergroups')) 
;
