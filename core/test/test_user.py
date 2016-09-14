# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from pytest import fixture, raises
from sqlalchemy.exc import IntegrityError
from core.test.asserts import assert_deprecation_warning
from core import config, db, User, UserGroup
from core.test.factories import UserGroupFactory
from contenttypes import Directory
from core.database.postgres.user import UserToUserGroup


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


def test_user_home_dir(user_with_home_dir):
    user = user_with_home_dir
    assert isinstance(user.home_dir, Directory)
    # home dir must have 3 special subdirs
    assert user.home_dir.children.count() == 2


def test_user_special_dirs(user_with_home_dir):
    user = user_with_home_dir
    home_subdirs = user.home_dir.children.all()
    assert user.upload_dir in home_subdirs
    assert user.trash_dir in home_subdirs


def test_user_create_home_dir(session, some_user, home_root):
    user = some_user
    session.add(home_root)
    home = user.create_home_dir()
    assert isinstance(home, Directory)
    home_subdirs = user.home_dir.children.all()
    assert user.upload_dir in home_subdirs
    assert user.trash_dir in home_subdirs
    assert home.has_read_access(user=user)
    assert home.has_write_access(user=user)
    assert home.has_data_access(user=user)


def test_get_or_add_private_group(session, some_user):
    group = some_user.get_or_add_private_group()
    assert isinstance(group, UserGroup)
    same_group_again = some_user.get_or_add_private_group()
    assert same_group_again is group


def test_add_another_private_group(session, some_user):
    """Private groups should never be created by hand (use Node.get_or_add_private_group).
    But, if you actually do that, this will happen some day:
    """
    with raises(IntegrityError):
        # ok
        some_user.get_or_add_private_group()
        # not ok, someone tries to add a second read private ruleset by hand...
        group = UserGroup(name=u"epic_fail")
        group_assoc = UserToUserGroup(usergroup=group, private=True)
        some_user.group_assocs.append(group_assoc)
        # flush to enforce constraints
        session.flush()

def test_add_another_user_to_private_group(session, some_user):
    """Private groups should never be created by hand (use Node.get_or_add_private_group).
    But, if you actually do that, this will happen some day:
    """
    with raises(IntegrityError):
        # ok, create and return user group for some_user
        private_group = some_user.get_or_add_private_group()
        # not ok, someone tries to add a second user
        another_user = User(login_name=u"epic_fail")
        group_assoc = UserToUserGroup(usergroup=private_group, private=True)
        another_user.group_assocs.append(group_assoc)
        # flush to enforce constraints
        session.flush()

def test_user_hidden_edit_functions(some_user, some_group):
    g1 = UserGroupFactory()
    g2 = UserGroupFactory(hidden_edit_functions=["func1", "func2"])
    g3 = UserGroupFactory(hidden_edit_functions=None)
    some_user.groups = [g1, g2, g3]
    hidden_edit_functions = some_user.hidden_edit_functions
    for f in g1.hidden_edit_functions:
        assert f in hidden_edit_functions


def test_guest_user_in_default_data(default_data):
    q = db.session.query
    assert q(User).filter_by(login_name=config.get_guest_name()).one()


def test_admin_user_in_default_data(default_data):
    q = db.session.query
    admin_username = config.get("user.adminuser")
    assert q(User).filter_by(login_name=admin_username).one()
