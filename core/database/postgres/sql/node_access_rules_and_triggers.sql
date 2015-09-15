DROP TRIGGER IF EXISTS node_to_access_rule_insert on :search_path.node_to_access_rule;
CREATE TRIGGER node_to_access_rule_insert
AFTER INSERT ON :search_path.node_to_access_rule
FOR EACH ROW 
WHEN (NEW.inherited = false)
EXECUTE PROCEDURE :search_path.on_node_to_access_rule_insert_delete();


DROP TRIGGER IF EXISTS node_to_access_rule_delete on :search_path.node_to_access_rule;
CREATE TRIGGER node_to_access_rule_delete
AFTER DELETE ON :search_path.node_to_access_rule
FOR EACH ROW 
WHEN (OLD.inherited = false)
EXECUTE PROCEDURE :search_path.on_node_to_access_rule_insert_delete();


DROP TRIGGER IF EXISTS node_to_access_ruleset_insert ON :search_path.node_to_access_ruleset;
CREATE TRIGGER node_to_access_ruleset_insert
AFTER INSERT ON :search_path.node_to_access_ruleset
FOR EACH ROW 
EXECUTE PROCEDURE :search_path.on_node_to_access_ruleset_insert();


DROP TRIGGER IF EXISTS node_to_access_ruleset_delete ON :search_path.node_to_access_ruleset;
CREATE TRIGGER node_to_access_ruleset_delete
AFTER DELETE ON :search_path.node_to_access_ruleset
FOR EACH ROW 
EXECUTE PROCEDURE :search_path.on_node_to_access_ruleset_delete();

