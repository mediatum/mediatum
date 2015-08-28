# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import fixture, raises


@fixture
def version(monkeypatch):
    import core.database.postgres.continuumext
    monkeypatch.setattr(core.database.postgres.continuumext, "parent_class", lambda c: ParentClass)

    from core.database.postgres.continuumext import MtVersionBase

    class ParentClass(object):

        def test_meth(self, a):
            return a

        @property
        def test_prop(self):
            return "works"

        @test_prop.setter
        def test_prop(self, value):
            pass

        test_attr = "works"

        def test_own_meth(self):
            return "wrong method, from parent class!"

    class VersionClass(MtVersionBase):

        def test_own_meth(self):
            return "own"

    return VersionClass()


def test_attr(version):
    assert version.test_attr == "works"


def test_method(version):
    assert version.test_meth("works") == "works"


def test_property(version):
    assert version.test_prop == "works"


def test_own_meth(version):
    assert version.test_own_meth() == "own"
