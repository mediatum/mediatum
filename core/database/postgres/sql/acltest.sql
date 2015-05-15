--EXPLAIN ANALYZE

SELECT distinct node.id, node.name, node.type, node.schema, node.orderpos FROM node
JOIN noderelation ON node.id=cid
JOIN node_to_access_rule na ON node.id=na.nid
JOIN access_rule a ON a.id=na.rule_id
WHERE noderelation.nid=604993
AND ruletype='read'
AND node.type in ('document', 'image', 'audio', 'collection', 'directory')
AND (subnets is NULL OR (invert_subnet # ('127.0.0.1' << ANY(subnets))))
AND (group_ids IS NULL OR (invert_group # (ARRAY[648465,645255,478029,956433,16437,16438,956507,331103] && group_ids)))
AND (dateranges IS NULL OR (invert_date # ('2015-04-07'::date <@ ANY(dateranges))))
;

EXPLAIN ANALYZE

SELECT distinct node.id, node.name, node.type, node.schema, node.orderpos FROM node
JOIN noderelation ON node.id=cid
JOIN node_to_access_rule na ON node.id=na.nid
JOIN access_rule a ON a.id=na.rule_id
WHERE noderelation.nid=604993
AND ruletype='write'
AND block=false
AND node.type in ('document', 'image', 'audio', 'collection', 'directory')
AND (subnets is NULL OR (invert_subnet # ('127.0.0.1' << ANY(subnets))))
AND (group_ids IS NULL OR (invert_group # (ARRAY[648465,645255,478029,956433,16437,16438,956507,331103] && group_ids)))
AND (dateranges IS NULL OR (invert_date # ('2015-04-07'::date <@ ANY(dateranges))))

EXCEPT

SELECT distinct node.id, node.name, node.type, node.schema, node.orderpos FROM node
JOIN noderelation ON node.id=cid
JOIN node_to_access_rule na ON node.id=na.nid
JOIN access_rule a ON a.id=na.rule_id
WHERE noderelation.nid=604993
AND ruletype='write'
AND block=true
AND node.type in ('document', 'image', 'audio', 'collection', 'directory')
AND (subnets is NULL OR (invert_subnet # ('127.0.0.1' << ANY(subnets))))
AND (group_ids IS NULL OR (invert_group # (ARRAY[648465,645255,478029,956433,16437,16438,956507,331103] && group_ids)))
AND (dateranges IS NULL OR (invert_date # ('2015-04-07'::date <@ ANY(dateranges))))
;
