CREATE OR REPLACE FUNCTION public.f_delfunc(_schema text, _del text = '') 
  RETURNS text
  LANGUAGE plpgsql 
AS
$BODY$
DECLARE
    _sql   text;
    _ct    text;

BEGIN
   SELECT INTO _sql, _ct
          string_agg('DROP '
                   || CASE p.proisagg WHEN true THEN 'AGGREGATE '
                                                ELSE 'FUNCTION ' END
                   || quote_ident(n.nspname) || '.' || quote_ident(p.proname)
                   || '('
                   || pg_catalog.pg_get_function_identity_arguments(p.oid)
                   || ');'
                  ,E'\n'
          )
          ,count(*)::text
   FROM   pg_catalog.pg_proc p
   LEFT   JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
   WHERE  n.nspname = _schema;
   -- AND p.proname ~~* 'f_%';                     -- Only selected funcs?
   -- AND pg_catalog.pg_function_is_visible(p.oid) -- Only visible funcs?

IF lower(_del) = 'del' THEN                        -- Actually delete!
   EXECUTE _sql;
   RETURN _ct || E' functions deleted:\n' || _sql;
ELSE                                               -- Else only show SQL.
   RETURN _ct || E' functions to delete:\n' || _sql;
END IF;

END;
$BODY$;


CREATE OR REPLACE FUNCTION msgtest() RETURNS VOID
    LANGUAGE plpgsql
    IMMUTABLE
    SET search_path = :search_path
    AS $f$
BEGIN
    RAISE DEBUG 'TEST DEBUG %', 1;
    RAISE LOG 'TEST LOG %', 2;
    RAISE INFO 'TEST INFO %', 3;
    RAISE NOTICE 'TEST NOTICE %', 4;
    RAISE WARNING 'TEST WARNING %', 5;
    RAISE EXCEPTION 'TEST EXCEPTION %', 6;
END;
$f$;
