# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from web.edit.modules.metadata import _handle_edit_metadata
from utils.testing import make_node_public
from schema import schema

# adding more test functions may fail, see the comments for the following imports
from core.test.test_version import teardown_module, session


def test_handle_edit_metadata_new_tagged_version(session, req, editor_user, some_node, simple_mask_with_maskitems):
    mask = simple_mask_with_maskitems
    nodes = [some_node]
    node = some_node
    make_node_public(some_node)
    schema.init()
    req.session["user_id"] = editor_user.id
    req.form["testattr"] = u"updated"
    session.commit()
    assert node.versions.count() == 1
    _handle_edit_metadata(req, mask, nodes)
    assert node["testattr"] == u"updated"
    session.commit()
    assert node.versions.count() == 2
