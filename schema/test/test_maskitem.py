# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises
from schema.schema import Metafield, Maskitem


def test_metafield(some_maskitem):
    assert isinstance(some_maskitem.metafield, Metafield) 
    
    
def test_set_metafield(some_maskitem, some_metafield):
    some_maskitem.metafield = some_metafield
    assert some_maskitem.metafield == some_metafield
    
    
def test_set_metafield_none(some_maskitem):
    some_maskitem.metafield = None
    assert some_maskitem.metafield is None
        
        
def test_mask_metafield_query_neq(some_mask, some_metafield):
    other_maskitems = some_mask.maskitems.filter(Maskitem.metafield != some_metafield).all()
    assert(some_metafield not in other_maskitems)
        
        
def test_mask_metafield_query_eq(some_mask):
    maskitem = some_mask.maskitems[0]
    metafield = maskitem.metafield
    maskitems_found = some_mask.maskitems.filter(Maskitem.metafield == metafield).all()
    assert(maskitem in maskitems_found)
        
        
def test_del_metafield(some_maskitem):
    with raises(AttributeError):
        del some_maskitem.metafield