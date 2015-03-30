CREATE TRIGGER mapping_insert INSTEAD OF INSERT ON nodemapping FOR EACH ROW EXECUTE PROCEDURE on_mapping_insert();

CREATE TRIGGER mapping_delete INSTEAD OF DELETE ON nodemapping FOR EACH ROW EXECUTE PROCEDURE on_mapping_delete();


-- CREATE OR REPLACE RULE noderelation_dupl_ignore AS
--     ON INSERT TO noderelation
--    WHERE (EXISTS ( SELECT 1
--            FROM noderelation
--           WHERE ((noderelation.nid = new.nid) AND (noderelation.cid = new.cid) AND (noderelation.distance = new.distance)))) DO INSTEAD NOTHING;

CREATE OR REPLACE RULE nodemapping_dupl_ignore AS
    ON INSERT TO nodemapping
   WHERE (EXISTS ( SELECT 1
           FROM nodemapping
          WHERE ((nodemapping.nid = new.nid) AND (nodemapping.cid = new.cid)))) DO INSTEAD NOTHING;

