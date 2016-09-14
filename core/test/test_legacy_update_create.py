# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from utils.date import parse_date
from core.test.factories import DocumentFactory

# adding more test functions may fail, see the comments for the following imports
from core.test.test_version import teardown_module, session


def test_create_update(session, req, guest_user, some_user, enable_athana_continuum_plugin):
    session.commit()
    req.session["user_id"] = some_user.id
    node = DocumentFactory()
    session.add(node)
    node["testattr"] = "new"
    session.commit()
    # well, guest users shouldn't update nodes, but it's ok for a test ;)
    req.session["user_id"] = guest_user.id
    node["testattr"] = "changed"
    session.commit()
    assert node.creator == some_user.getName()
    assert node.updateuser == guest_user.getName()
    assert node.creationtime <= node.updatetime 
    assert parse_date(node.updatetime)
    