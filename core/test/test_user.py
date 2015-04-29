# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import fixture
from core.test.asserts import assert_deprecation_warning
from core import db, User, ShoppingBag


@fixture(params=[
    User.getGroups,
    User.getLastName,
    User.getFirstName,
    User.getTelephone,
    User.getComment,
    User.getEmail,
    User.isAdmin,
    User.isEditor,
    User.isWorkflowEditor,
    User.getOrganisation,
    User.getUserID,
])
def legacy_getter(request):
    return request.param


def test_legacy_getter_deprecation(some_user, legacy_getter):
    assert_deprecation_warning(legacy_getter, some_user)


def test_add_shoppingbag(some_user):
    shopping_bag = ShoppingBag("test")
    some_user.shoppingbags["test"] = shopping_bag
    user = db.session.query(User).filter(User.shoppingbags.contains(shopping_bag)).one()
    assert len(user.shoppingbags) == 1


def test_admin_user(admin_user):
    assert not admin_user.is_workflow_editor
    assert not admin_user.is_editor
    assert admin_user.is_admin


def test_editor_user(editor_user):
    assert not editor_user.is_workflow_editor
    assert editor_user.is_editor
    assert not editor_user.is_admin


def test_workflow_editor_user(workflow_editor_user):
    assert workflow_editor_user.is_workflow_editor
    assert not workflow_editor_user.is_editor
    assert not workflow_editor_user.is_admin
