# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import fixture, raises
from core.search import parser, language
from core.search.representation import Or, And, Not, FullMatch, FulltextMatch, AttributeMatch, AttributeCompare, TypeMatch, SchemaMatch
from parcon import ParseException


@fixture(params=[
    (u"full = München", FullMatch(u"München")),
    (u"fulltext = München", FulltextMatch(u"München")),
    (u"city = München", AttributeMatch(u"city", u"München")),
    (u"city eq München", AttributeCompare(u"city", u"eq", u"München")),
    (u"city eq \"München\"", AttributeCompare(u"city", u"eq", u"München")),
    (u"year < 2014", AttributeCompare(u"year", u"<", u"2014")),
    (u"year <= 2014", AttributeCompare(u"year", u"<=", u"2014")),
    (u"year > 2014", AttributeCompare(u"year", u">", u"2014")),
    (u"year <= 2014", AttributeCompare(u"year", u"<=", u"2014")),
    (u"objtype = document", TypeMatch(u"document")),
    (u"schema = buch", SchemaMatch(u"buch"))])
def simple_query(request):
    return request.param


def test_parse_maybe_quoted_bare():
    assert language.maybe_quoted.parse_string(u"München") == u"München"


def test_parse_maybe_quoted_quoted():
    assert language.maybe_quoted.parse_string(u"\"München\"") == u"München"


def test_parse_unicode():
    text = u"πλανήτης\uEEEE"
    st = parser.parse_string(u"full=" + text)
    assert st == FullMatch(text)


def test_parse_invalid_value():
    from core.search.language import value
    with raises(ParseException):
        value.parse_string(u"gtrg\u0022gre")


def test_parse_simple_query(simple_query):
    searchquery, expected = simple_query
    st = parser.parse_string(searchquery)
    assert st == expected


def test_parse_full_unicode_quoted():
    text = u'"Öffentliche schöne Häuser in München"'
    st = parser.parse_string(u'full=' + text)
    assert st == FullMatch(text.strip('"'))


def test_parse_plain_or():
    st = parser.parse_string(u'full=haus or full=ofit')
    assert st == Or(FullMatch(u"haus"), FullMatch(u"ofit"))


def test_parse_plain_and():
    st = parser.parse_string(u'full=haus and full=ofit')
    assert st == And(FullMatch(u"haus"), FullMatch(u"ofit"))


def test_parse_not():
    st = parser.parse_string(u'not(full=torpedo)')
    assert st == Not(FullMatch(u"torpedo"))


def test_parse_combined():
    searchquery = u"((fulltext=münchen) OR (title=münchen)) AND ((NOT (full=Strauß)) OR (year > 2000))"
    st = parser.parse_string(searchquery)
    left = Or(FulltextMatch(u"münchen"), AttributeMatch(u"title", u"münchen"))
    right = Or(Not(FullMatch(u"Strauß")), AttributeCompare(u"year", ">", u"2000"))
    assert isinstance(st, And)
    assert st.left == left
    assert st.right == right


def test_parse_quoted_searchstring_with_operators():
    searchquery = u'full="haus AND hof"'