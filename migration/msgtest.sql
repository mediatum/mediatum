CREATE OR REPLACE FUNCTION mediatum.msgtest() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS $f$

BEGIN
    RAISE NOTICE 'notice';
END;
$f$;
