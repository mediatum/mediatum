# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details

Some tests for DeclarativeBase extensions.
"""

from core.database.postgres import __str__
from pytest import fixture


@fixture
def clazz():
    class Cls(object):

        def __repr__(self):
            return "tästrepr"

    Cls.__str__ = __str__

    return Cls


def test_str_from_repr(clazz):

    a = clazz()
    assert str(a) == "tästrepr"


def test_str_from_unicode(clazz):

    def f(self):
        return u"tästunicode"

    clazz.__unicode__ = f

    a = clazz()
    assert str(a) == "tästunicode"
