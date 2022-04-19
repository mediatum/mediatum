DROP TRIGGER IF EXISTS mapping_insert ON :search_path.nodemapping;
CREATE TRIGGER mapping_insert INSTEAD OF INSERT ON :search_path.nodemapping FOR EACH ROW EXECUTE PROCEDURE :search_path.on_mapping_insert();

DROP TRIGGER IF EXISTS mapping_delete ON :search_path.nodemapping;
CREATE TRIGGER mapping_delete INSTEAD OF DELETE ON :search_path.nodemapping FOR EACH ROW EXECUTE PROCEDURE :search_path.on_mapping_delete();


-- CREATE OR REPLACE RULE noderelation_dupl_ignore AS
--     ON INSERT TO noderelation
--    WHERE (EXISTS ( SELECT 1
--            FROM noderelation
--           WHERE ((noderelation.nid = new.nid) AND (noderelation.cid = new.cid) AND (noderelation.distance = new.distance)))) DO INSTEAD NOTHING;

CREATE OR REPLACE RULE nodemapping_dupl_ignore AS
    ON INSERT TO :search_path.nodemapping
   WHERE (EXISTS ( SELECT 1
           FROM :search_path.nodemapping
          WHERE ((:search_path.nodemapping.nid = new.nid) AND (:search_path.nodemapping.cid = new.cid)))) DO INSTEAD NOTHING;

