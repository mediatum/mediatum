# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
from core.test.asserts import assert_deprecation_warning


def test_getGroup_id(some_group):
    from core.usergroups import getGroup
    from core import db
    db.session.flush()
    group = assert_deprecation_warning(getGroup, some_group.id)
    assert group == some_group
    
    
def test_getGroup_name(group_node_with_some_group):
    from core.usergroups import getGroup
    some_group = group_node_with_some_group.children[0]
    group = assert_deprecation_warning(getGroup, some_group.name)
    assert group == some_group
    