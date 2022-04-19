DO $$ BEGIN
    CREATE TYPE mediatum_import.expanded_accessrule AS (expanded_rule text, rulesets text[], special_rulestrings text[]);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE OR REPLACE FUNCTION mediatum_import.expand_acl_rule(rulestr text)
  RETURNS mediatum_import.expanded_accessrule
  LANGUAGE plpgsql 
  SET search_path = mediatum_import
  STABLE  
AS $f$
DECLARE
    expanded mediatum_import.expanded_accessrule;
BEGIN
SELECT array_to_string(array_agg(
                               (SELECT CASE WHEN n LIKE '{%' THEN n ELSE
                                  (SELECT rule
                                   FROM access
                                WHERE name = n) END)),',') as expanded_rule,
       array_agg(
               (SELECT trim(' ' from n)
                WHERE n NOT LIKE '{%')) as rulesets,
       array_agg(
               (SELECT trim(' ' from n)
                WHERE n LIKE '{%')) as special_rulestrings
INTO expanded
FROM unnest(regexp_split_to_array(trim(', ' from rulestr), ',')) AS n;
RETURN expanded;
END;
$f$;

