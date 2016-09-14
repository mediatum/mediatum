# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.database.postgres.alchemyext import exec_sqlfunc
from core.database.postgres import mediatumfunc


def test_jsonb_limit_to_size_int(session):
    res = exec_sqlfunc(session, mediatumfunc.jsonb_limit_to_size('42'))
    assert res == 42


def test_jsonb_limit_to_size_str_unmodified(session):
    # function gets a string that will be converted to JSONB,
    # but we get back a python string (psycopg loads the JSON for us)
    res = exec_sqlfunc(session, mediatumfunc.jsonb_limit_to_size('"42"'))
    assert res == '42'


def test_jsonb_limit_to_size_str_limited(session):
    res = exec_sqlfunc(session, mediatumfunc.jsonb_limit_to_size('"42"', 1))
    assert res == '4'