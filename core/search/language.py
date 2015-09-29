# -*- coding: utf-8 -*-
"""
    Define the search language as parcon expression.
    Use `parser.parse_string(s)` to convert a query string to the search tree representation.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import re
import string
from parcon import Literal, SignificantLiteral, Word, InfixExpr, Forward, AnyCase, Regex, Expected
from core.search.untilregex import UntilRegex
from core.search.representation import AttributeMatch, FullMatch, SchemaMatch, FulltextMatch, AttributeCompare, TypeMatch, And, Or, Not

# some parcon shortcuts
L = Literal
SL = SignificantLiteral
AC = AnyCase


VALUE_CHAR_REGEX = u"[\u0020\u0021\u0023-\uD7FF\u0009\u000A\u000D\uE000-\uFFFD\u10000-\u10FFFF]+"


def _join(seq):
    return "".join(seq)

compare_op = (SL(">=") | SL("<=") | SL(">") | SL("<"))(name="compare_op")
attr_name = Word(string.letters + string.digits + "_" + "-" + ".")(desc="attribute")
value = Expected(Regex(VALUE_CHAR_REGEX), "value")(desc="value")
bare_value = UntilRegex(u"\s*(?:\sor\s|\sand\s|[)(])", flags=re.IGNORECASE | re.UNICODE) | value  # may end with or | and | ( | )
maybe_quoted = (SL('"') + value + SL('"'))[_join] | bare_value

attr_match = (attr_name + "=" + maybe_quoted)(name="attr_match")[AttributeMatch.tup]
full_match = (L("full") + "=" + maybe_quoted)(name="full_match")[FullMatch]
schema_match = (L("schema") + "=" + maybe_quoted)(name="schema_match")[SchemaMatch]
type_match = (L("objtype") + "=" + maybe_quoted)(name="type_match")[TypeMatch]
fulltext_match = (L("fulltext") + "=" + maybe_quoted)(name="fulltext_match")[FulltextMatch]
attr_compare = (attr_name + compare_op + maybe_quoted)(name="attr_compare")[AttributeCompare.tup]
atom = (schema_match | type_match | fulltext_match | full_match | attr_match | attr_compare)(name="atom")

expr = Forward()
t = atom | "(" + expr + ")"
t = InfixExpr(t, [(AC("and"), And)])
t = InfixExpr(t, [(AC("or"), Or)])
negated = (AC("not") + t)[Not]
t = negated | t

expr << t(name="search_expr")

# expr is used for parsing the search language, name it `parser` to make it clearer ;)
parser = expr
