 -- show duplicate rules

SELECT rule_ids[1] AS surviving_rule,
       rule_ids[2:cardinality(rule_ids)] AS duplicates
FROM
  (SELECT array_agg(id) AS rule_ids,
          count(*)
   FROM access_rule
   GROUP BY invert_subnet,
            invert_date,
            invert_group,
            group_ids,
            subnets,
            dateranges HAVING count(*) > 1
   ORDER BY count(*) DESC) r ;

