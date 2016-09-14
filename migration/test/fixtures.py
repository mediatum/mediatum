# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import os.path
from munch import Munch
from pytest import fixture
from migration.test.factories import AccessFactory, IPListFactory, AccessRulesetFactory
from migration.test.factories import ImportNodeFactory
from core.database.postgres.permission import AccessRule, AccessRuleset, AccessRulesetToRule
from core.test.factories import DirectoryFactory, NodeFactory
from ipaddr import IPv4Network
from core.database.postgres.connector import read_and_prepare_sql


@fixture(scope="session")
def database(database):
    """Drop/create mediatum_import schema"""
    from core import db
    with db.engine.begin() as conn:
        conn.execute = conn.execute
        conn.execute("DROP SCHEMA IF EXISTS mediatum_import CASCADE")
        conn.execute("CREATE SCHEMA mediatum_import")
        sql_dir = os.path.join(os.path.dirname(__file__), "..")
        conn.execute(read_and_prepare_sql("acl_migration.sql", sql_dir=sql_dir))
        conn.execute(read_and_prepare_sql("user_migration.sql", sql_dir=sql_dir))
        conn.execute(read_and_prepare_sql("migration.sql", sql_dir=sql_dir))

    from migration.import_datamodel import ImportBase
    ImportBase.metadata.bind = db.engine
    ImportBase.metadata.create_all()
    return db


@fixture
def import_node_with_simple_access():
    node = NodeFactory(id=100)
    import_node = ImportNodeFactory(
        id=100,
        readaccess=u"{ group test_readers }",
        writeaccess=u"{ group test_writers }",
        dataaccess=u"{ group test_datausers }")
    return import_node


@fixture
def import_node_with_stupid_commas_in_readaccess():
    node = NodeFactory(id=100)
    import_node = ImportNodeFactory(
        id=100,
        readaccess=u",nicht Jeder,{ group test_readers },,")
    return import_node


@fixture
def import_node_with_complex_access():
    node = NodeFactory(id=100)
    import_node = ImportNodeFactory(id=100,
                                    readaccess=u"{ NOT ( group test_readers OR group test_readers2 ) }")
    return import_node


@fixture
def import_node_with_ruleset(session):
    node = NodeFactory(id=100)
    session.flush()
    acl1 = AccessFactory(rule=u"( group test_readers OR group test_readers2 )", name=u"not_rule")
    import_node = ImportNodeFactory(id=100, readaccess=u"not_rule,{ user darfdas }")
    return import_node


@fixture
def import_node_with_non_dnf_ruleset(session):
    node = NodeFactory(id=100)
    session.flush()
    acl1 = AccessFactory(rule=u"NOT ( group test_readers OR group test_readers2 )", name=u"not_rule")
    import_node = ImportNodeFactory(id=100, readaccess=u"not_rule,{ user darfdas }")
    return import_node


@fixture
def user_nodes(session):
    users_root = NodeFactory(name=u"users", type=u"users")
    u1 = NodeFactory(name=u"testuser1", type=u"user")
    u2 = NodeFactory(name=u"testuser2", type=u"user")
    users = [u1, u2]
    users_root.children.extend(users)
    return users


@fixture
def usergroup_nodes(session):
    usergroups_root = NodeFactory(name=u"usergroups", type=u"usergroups")
    ug1 = NodeFactory(name=u"testgroup1", type=u"usergroup")
    ug2 = NodeFactory(name=u"testgroup2", type=u"usergroup")
    usergroups = [ug1, ug2]
    usergroups_root.children.extend(usergroups)
    return usergroups


@fixture
def user_nodes_with_groups(user_nodes, usergroup_nodes):
    ug1, ug2 = usergroup_nodes
    u1, _ = user_nodes
    ug1.children.extend(user_nodes)
    ug2.children.append(u1)
    return Munch(users=user_nodes, groups=usergroup_nodes)


@fixture
def users_and_groups_for_ruleset(session, internal_authenticator_info):
    from core import User, UserGroup

    users = [User(login_name=u"darfdas", authenticator_info=internal_authenticator_info)]
    session.add_all(users)

    groups = [UserGroup(name=u"test_readers"), UserGroup(name=u"test_readers2")]
    session.add_all(groups)
    return users, groups


@fixture
def ruleset(session, users_and_groups_for_ruleset):
    users, groups = users_and_groups_for_ruleset
    rs = AccessRulesetFactory(name="not_rule")
    rule = AccessRule(group_ids=[g.id for g in groups] + [u.get_or_add_private_group().id for u in users])
    rs.rule_assocs.append(AccessRulesetToRule(rule=rule))
    return rs


@fixture
def two_access_rules():
    rule1 = AccessRule(group_ids=[11, 12], invert_group=True)
    rule2 = AccessRule(group_ids=[13], subnets=[IPv4Network("127.0.0.1/32")])
    return rule1, rule2


@fixture
def two_access_rulesets():
    ruleset1 = AccessRuleset(name=u"Ruleset1")
    ruleset2 = AccessRuleset(name=u"Ruleset2")
    return ruleset1, ruleset2


@fixture
def some_numbered_nodes():
    return [DirectoryFactory(id=j) for j in range(1, 4)]


@fixture
def first_version_node():
    node = NodeFactory(id=100001, schema=u"testschema")
    node.system_attrs[u"version.id"] = u"1"
    node.system_attrs[u"version.comment"] = u"first"
    return node


@fixture
def middle_version_node():
    node = NodeFactory(id=100002, schema=u"testschema")
    node.system_attrs[u"version.id"] = u"2"
    node.system_attrs[u"version.comment"] = u"middle"
    return node


@fixture
def current_version_node():
    node = NodeFactory(id=100003, schema=u"testschema")
    node.system_attrs[u"version.id"] = u"3"
    node.system_attrs[u"version.comment"] = u"current"
    return node


@fixture
def some_iplist():
    iplist = IPListFactory()
    return iplist
