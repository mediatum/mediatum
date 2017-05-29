# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core.test.asserts import assert_deprecation_warning
from schema.schema import Maskitem
from schema.test.fixtures import some_mask_with_maskitem


def test_all_maskitems_flat(some_mask_with_maskitem):
    from core import db
    db.session.flush()
    maskitems = some_mask_with_maskitem.all_maskitems
    assert maskitems.count() == 1
    assert(isinstance(maskitems[0], Maskitem))


def test_all_maskitems_nested(some_mask_with_nested_maskitem):
    from core import db
    db.session.flush()
    maskitems = some_mask_with_nested_maskitem.all_maskitems
    assert maskitems.count() == 2
    for mi in maskitems:
        assert(isinstance(mi, Maskitem))


def test_getMaskFields_first_level(some_mask):
    maskitems = assert_deprecation_warning(some_mask.getMaskFields, first_level_only=True)
    # maskitems is of type InstrumentedList
    assert isinstance(maskitems[0], Maskitem)


def test_getMaskFields(some_mask):
    from core import db
    db.session.flush()
    maskitems = assert_deprecation_warning(some_mask.getMaskFields)
    # maskitems is of type MtQuery
    assert isinstance(maskitems.first(), Maskitem)
