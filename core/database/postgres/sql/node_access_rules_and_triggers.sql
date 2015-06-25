CREATE TRIGGER node_to_access_rule_insert_delete
AFTER INSERT OR DELETE ON :search_path.node_to_access_rule
FOR EACH ROW 
EXECUTE PROCEDURE :search_path.on_node_to_access_rule_insert_delete();


CREATE TRIGGER node_to_access_ruleset_insert
AFTER INSERT ON :search_path.node_to_access_ruleset
FOR EACH ROW 
EXECUTE PROCEDURE :search_path.on_node_to_access_ruleset_insert();


CREATE TRIGGER node_to_access_ruleset_delete
AFTER DELETE ON :search_path.node_to_access_ruleset
FOR EACH ROW 
EXECUTE PROCEDURE :search_path.on_node_to_access_ruleset_delete();

