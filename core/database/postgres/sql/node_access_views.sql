
CREATE OR REPLACE VIEW rules_for_node AS 
 SELECT na.nid,
    na.rule_id,
    na.ruletype,
    na.invert,
    na.inherited,
    na.blocking,
    a.invert_subnet,
    a.invert_date,
    a.invert_group,
    (SELECT group_ids_to_names(a.group_ids)) AS groups,
    a.subnets,
    a.dateranges
   FROM node_to_access_rule na
     JOIN access_rule a ON na.rule_id = a.id;
     
     
     
CREATE OR REPLACE VIEW rules_for_ruleset AS 
 SELECT access_ruleset_to_rule.ruleset_name,
    access_ruleset_to_rule.rule_id,
    access_ruleset_to_rule.invert,
    access_ruleset_to_rule.blocking,
    a.invert_subnet,
    a.invert_date,
    a.invert_group,
    (SELECT group_ids_to_names(a.group_ids)) AS groups,
    a.subnets,
    a.dateranges
   FROM access_ruleset_to_rule
     JOIN access_rule a ON access_ruleset_to_rule.rule_id = a.id;
