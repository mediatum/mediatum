# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
from core.test.asserts import assert_deprecation_warning


def test_getUser_id(some_user):
    from core.users import getUser
    from core import db
    db.session.flush()
    user = assert_deprecation_warning(getUser, some_user.id)
    assert user == some_user
    
    
def test_getUser_name(users_node_with_some_user):
    from core.users import getUser
    some_user = users_node_with_some_user.children[0]
    user = getUser(some_user.name)
    assert user == some_user
    
    
def test_getUser_userkey(users_node_with_some_user):
    from core.users import getUser
    some_user = users_node_with_some_user.children[0]
    user = getUser(some_user["service.userkey"])
    assert user == some_user
    