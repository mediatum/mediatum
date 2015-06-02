SET search_path to mediatum_import;

CREATE TYPE expanded_accessrule AS (expanded_rule text, rulesets text[]);

CREATE OR REPLACE FUNCTION mediatum_import.expand_acl_rule(rulestr text)
  RETURNS expanded_accessrule
  LANGUAGE plpgsql 
  STABLE  
AS $f$
DECLARE
    expanded expanded_accessrule;
BEGIN
SELECT array_to_string(array_agg(
                               (SELECT CASE WHEN n LIKE '{%' THEN n ELSE
                                  (SELECT RULE
                                   FROM ACCESS
                                WHERE name = n) END)),',') as expanded_rule,
       array_agg(
               (SELECT n
                WHERE n NOT LIKE '{%')) as rulesets
INTO expanded
FROM unnest(regexp_split_to_array(rulestr, ',')) AS n;
RETURN expanded;
END;
$f$