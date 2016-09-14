# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""


def test_migrate_internal_users_users(session, user_nodes):
    u1, u2 = user_nodes
    session.flush()
    session.execute("SELECT migrate_internal_users()")
    from core import User
    q = session.query
    session.flush()
    migrated_users = q(User).all()
    assert len(migrated_users) == 2
    mu1, mu2 = migrated_users
    assert mu1.login_name == u1.name
    assert mu2.login_name == u2.name


def test_migrate_usergroups(session, usergroup_nodes):
    ug1, ug2 = usergroup_nodes
    session.flush()
    session.execute("SELECT migrate_usergroups()")
    from core import UserGroup
    q = session.query
    migrated_usergroups = q(UserGroup).all()
    assert len(migrated_usergroups) == 2
    mug1, mug2 = migrated_usergroups
    assert mug1.name == ug1.name
    assert mug2.name == ug2.name


def test_migrate_internal_users_users_and_groups(session, user_nodes_with_groups):
    u1, u2 = user_nodes_with_groups.users
    ug1, ug2 = user_nodes_with_groups.groups
    session.flush()
    session.execute("SELECT migrate_usergroups()")
    session.execute("SELECT migrate_internal_users()")
    from core import User, UserToUserGroup
    q = session.query
    assert q(UserToUserGroup).count() == 3
    # private rules are generated on-demand, migrated assocs must all be non-private
    assert q(UserToUserGroup).filter_by(private=True).count() == 0
    migrated_users = q(User).all()
    mu1, mu2 = migrated_users
    assert set(mu1.group_names) == set([ug1.name, ug2.name])
    assert set(mu2.group_names) == set([ug1.name])
