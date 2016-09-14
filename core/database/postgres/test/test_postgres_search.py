# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Postgres-specific search tests
"""
from pytest import raises
from core.search import SearchQueryException
from core.database.postgres.search import _prepare_searchstring


def test_prepare_searchstring_simple():
    searchstring = u' "python"  '
    res = _prepare_searchstring("|", searchstring)
    assert res == u"python"


def test_prepare_searchstring_empty():
    searchstring = u""
    with raises(SearchQueryException):
        _prepare_searchstring("|", searchstring)


def test_prepare_searchstring_or():
    searchstring = u'python nim scala'
    res = _prepare_searchstring("|", searchstring)
    assert res == u"python|nim|scala"


def test_prepare_searchstring_and():
    searchstring = u'python nim scala'
    res = _prepare_searchstring("&", searchstring)
    assert res == u"python&nim&scala"


def test_prepare_searchstring_or_prefix():
    searchstring = u'pyth* ni* sca*'
    res = _prepare_searchstring("|", searchstring)
    assert res == u"pyth:*|ni:*|sca:*"


def test_prepare_searchstring_multiple_stars():
    searchstring = u"pyth**o*n ni** sca***"
    res = _prepare_searchstring("|", searchstring)
    assert res == u"pyth:*|ni:*|sca:*"


def test_prepare_searchstring_only_star():
    searchstring = u"*"
    with raises(SearchQueryException):
        _prepare_searchstring("|", searchstring)


def test_prepare_searchstring_leading_stars():
    searchstring = u"**o*n **"
    res = _prepare_searchstring("|", searchstring)
    assert res == u"o:*"


def test_prepare_searchstring_leading_regex_wildcard():
    searchstring = u".*Authorname*"
    res = _prepare_searchstring("|", searchstring)
    assert res == u"Authorname:*"


def test_prepare_searchstring_leading_regex_wildcard_space():
    searchstring = u".*Authorname, A.*"
    res = _prepare_searchstring("|", searchstring)
    assert res == u"Authorname,|A.:*"


def test_prepare_searchstring_leading_stars_only_in_one():
    searchstring = u"pyth* ni *la"
    res = _prepare_searchstring("|", searchstring)
    assert res == u"pyth:*|ni|la"


def test_prepare_searchstring_postgres_operators():
    searchstring=u'|&:"!)(\\'
    res = _prepare_searchstring("|", searchstring)
    assert res == ur'\|\&\:\"\!\)\(\\'
