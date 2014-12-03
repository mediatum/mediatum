# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from utils.magicobjects import MInt


def test_mint_add():
    three = MInt(3)
    four = MInt(4)
    assert three + four == 7
    
    
def test_mint_concat_left():
    three = MInt(3)
    assert "TEST" + three == "TEST3"

    
def test_mint_concat_right():
    three = MInt(3)
    assert three + "TEST" == "3TEST"


def test_mint_unicode():
    three = MInt(3)
    assert unicode(three) == u"3"