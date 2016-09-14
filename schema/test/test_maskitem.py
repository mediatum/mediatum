# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises
from core import db, Node
from schema.schema import Metafield, Maskitem


def test_metafield(some_maskitem):
    assert isinstance(some_maskitem.metafield, Metafield)


def test_set_metafield(some_metafield):
    maskitem = Maskitem()
    db.session.add(maskitem)
    maskitem.metafield = some_metafield
    assert maskitem.metafield == some_metafield


def test_set_metafield_none(some_maskitem):
    with raises(ValueError):
        some_maskitem.metafield = None



def test_del_metafield(some_maskitem):
    with raises(AttributeError):
        del some_maskitem.metafield
