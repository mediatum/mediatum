-- getrennte Suche, dann UNION
-- recht schnell, nutzt passende Idx

select node.id, name
FROM to_tsquery('simple', 'München') qq, node
JOIN fulltext ON node.id=nid
JOIN fts ON fulltext.id=fulltext_id
WHERE 
config = 'simple'::regconfig 
AND fts.tsvec @@ qq

UNION ALL

select node.id, name 
FROM to_tsquery('simple', 'München') qq, node
WHERE jsonb_object_values_to_tsvector('simple', attrs) @@ qq


-- verbundene Suche, mit outer join
-- ziemlich langsam, da WHERE gemeinsam gecheckt wird und fts-:idx ignoriert wird

select node.id, name
FROM to_tsquery('simple', 'München') qq, node
LEFT OUTER JOIN fulltext ON node.id=nid
JOIN fts ON fulltext.id=fulltext_id
WHERE (config = 'simple'::regconfig AND fts.tsvec @@ qq)
OR jsonb_object_values_to_tsvector('simple', attrs) @@ qq
 

-- direkt, mit fulltext in der Node-tabelle

select node.id, name
FROM to_tsquery('german', 'München') qq, to_tsquery('german', 'Hamburg') qs, node

JOIN noderelation ON id=cid
WHERE 
nid=604993
AND 
(to_tsvector_safe('german', fulltext) @@ qq
OR to_tsvector_safe('german', fulltext) @@ qs
OR jsonb_object_values_to_tsvector('german', attrs) @@ qq
OR jsonb_object_values_to_tsvector('german', attrs) @@ qs
)


