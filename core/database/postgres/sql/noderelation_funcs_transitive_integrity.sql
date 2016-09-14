CREATE TYPE integrity_check_noderelation AS (nid integer, cid integer, distance integer, reason text);

-- calculates the transitive closure of the node tree and compares the result with the contents of noderelation
CREATE OR REPLACE FUNCTION check_transitive_integrity() RETURNS SETOF integrity_check_noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
RETURN QUERY
    WITH closure AS (SELECT * FROM transitive_closure())
    (SELECT *, 'missing' FROM closure EXCEPT SELECT *, 'missing' from noderelation)
    UNION ALL
    (SELECT *, 'excess' FROM noderelation EXCEPT SELECT *, 'excess' FROM closure);
END;
$$;

CREATE OR REPLACE FUNCTION fix_transitive_integrity() RETURNS SETOF integrity_check_noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
RETURN QUERY
    WITH closure AS (SELECT * FROM transitive_closure())
    , excess AS (SELECT * FROM noderelation EXCEPT SELECT * from closure)
    , missing AS (SELECT * FROM closure EXCEPT SELECT * from noderelation)
    , ins AS (INSERT INTO noderelation SELECT * FROM missing)
    , del AS (DELETE FROM noderelation nr WHERE (nr.nid, nr.cid, nr.distance) IN (SELECT * FROM excess))

    (SELECT *, 'missing' FROM missing)
    UNION ALL
    (SELECT *, 'excess' FROM excess);
END;
$$;

CREATE OR REPLACE FUNCTION compare_noderelation_with_backup() RETURNS SETOF integrity_check_noderelation
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
BEGIN
RETURN QUERY
    (SELECT *, 'missing' FROM backup.noderelation EXCEPT SELECT *, 'missing' FROM noderelation)
    UNION ALL
    (SELECT *, 'excess' FROM noderelation EXCEPT SELECT *, 'excess' FROM backup.noderelation);
END;
$$;
