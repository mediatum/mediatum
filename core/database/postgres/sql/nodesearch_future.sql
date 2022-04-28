-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

-- we don't need these functions at the moment, but they could be useful in the future ;)

CREATE OR REPLACE FUNCTION create_fts_entry(config regconfig, fulltext_id integer) RETURNS :search_path.fts
    LANGUAGE plpgsql
    SET search_path = :search_path
    AS $$
DECLARE
    text text;
    tsvec tsvector;
BEGIN
    SELECT fulltext INTO text FROM fulltext WHERE id=fulltext_id;
    tsvec = to_tsvector_safe(config, text);
    RETURN (fulltext_id, config, tsvec);
END;
$$;


CREATE OR REPLACE FUNCTION py_guess_language(text text) RETURNS text
   LANGUAGE plpython3u
    SET search_path = :search_path
    AS $$

    import guess_language
    try:
        lang = guess_language.guess_language(text)
    except:
        lang = None

    return lang
$$;


