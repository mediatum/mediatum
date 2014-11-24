# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from core.test.asserts import assert_deprecation_warning
from schema.schema import Maskitem


def test_getMaskFields(some_mask):
    maskitems = assert_deprecation_warning(some_mask.getMaskFields)
    assert isinstance(maskitems.first(), Maskitem)