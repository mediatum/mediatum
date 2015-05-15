  SELECT node FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype='write'
    AND na.blocking = false
    AND node.id = 1
    AND check_access_rule(a, ARRAY[5], :ip::inet, current_date)

    EXCEPT

    SELECT access_rule FROM node 
    JOIN node_to_access_rule na on node.id=na.nid
    JOIN access_rule a on na.rule_id=a.id
    WHERE na.ruletype='write'
    AND na.blocking = true
    AND node.id = 1
    AND NOT check_access_rule(a, ARRAY[5], :ip::inet, current_date);

