-- Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
-- SPDX-License-Identifier: AGPL-3.0-or-later

CREATE OR REPLACE FUNCTION mediatum.msgtest() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO :search_path
    AS $f$

BEGIN
    RAISE NOTICE 'notice';
END;
$f$;
