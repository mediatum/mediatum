CREATE OR REPLACE FUNCTION jsonb_object_values(obj jsonb) RETURNS SETOF jsonb
    LANGUAGE plpgsql
    IMMUTABLE
    SET search_path = :search_path
    AS $f$
BEGIN
    RETURN QUERY select value from jsonb_each(obj);
END;
$f$;


CREATE OR REPLACE FUNCTION jsonb_object_values_text(obj jsonb) RETURNS SETOF text
    LANGUAGE plpgsql
    IMMUTABLE
    SET search_path = :search_path
    AS $f$
BEGIN
    RETURN QUERY select value from jsonb_each_text(obj);
END;
$f$;


CREATE OR REPLACE FUNCTION jsonb_object_values_text_concat(obj jsonb, delim text) RETURNS text
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
DECLARE
    concat text;
BEGIN
    SELECT array_to_string(array_agg(f.value), delim) INTO concat FROM jsonb_each_text(obj) f;
    RETURN concat;
END;
$f$;


CREATE OR REPLACE FUNCTION jsonb_object_values(obj jsonb) RETURNS SETOF jsonb
    LANGUAGE plpgsql
    IMMUTABLE
    SET search_path = :search_path
    AS $f$
BEGIN
    RETURN QUERY select value from jsonb_each(obj);
END;
$f$;


CREATE OR REPLACE FUNCTION jsonb_object_values_to_tsvector(config regconfig, obj jsonb) RETURNS tsvector
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
DECLARE
    tsvec tsvector;
BEGIN
    tsvec = to_tsvector(config, jsonb_object_values_text_concat(obj, '|'));
    RETURN tsvec;
END;
$f$;


CREATE OR REPLACE FUNCTION to_numeric(src text) RETURNS numeric
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
DECLARE
    conv numeric;
BEGIN
    BEGIN
        conv := src::numeric;
    EXCEPTION WHEN OTHERS THEN
        RETURN NULL;
    END;

    RETURN conv;
END;
$f$;


CREATE OR REPLACE FUNCTION jsonb_object_delete_keys(jsonb jsonb, variadic keys_to_delete text[]) RETURNS jsonb
    LANGUAGE plpgsql
    SET search_path = :search_path
    IMMUTABLE
    AS $f$
DECLARE
    res jsonb;
BEGIN
    SELECT INTO res COALESCE(
      (SELECT ('{' || string_agg(to_json(key) || ':' || value, ',') || '}')
       FROM jsonb_each(jsonb)
       WHERE "key" <> ALL ("keys_to_delete")),
      '{}'
    )::jsonb;

    RETURN res;
END;
$f$;
