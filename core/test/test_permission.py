# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises
from sqlalchemy.exc import IntegrityError
from core import AccessRule, AccessRuleset, NodeToAccessRule, NodeToAccessRuleset
from core import db
from core.database.postgres import mediatumfunc
from utils.testing import make_node_public


def test_access_rules_query(some_node):
    node = some_node
    rr = AccessRule(group_ids=[1])
    rw = AccessRule(group_ids=[2])
    node.access_rule_assocs.append(NodeToAccessRule(rule=rr, ruletype="read"))
    node.access_rule_assocs.append(NodeToAccessRule(rule=rw, ruletype="write", invert=True, blocking=True))
    assert node.access_rule_assocs.filter_by(ruletype="read").one().rule == rr
    assert (node.access_rule_assocs.filter_by(ruletype="write", invert=True, blocking=True).one().rule == rw)


def test_access_get_inherited_access_ruleset_assocs(some_node_with_two_parents):
    node = some_node_with_two_parents
    rs1 = AccessRuleset(name=u"test", description=u"fake")
    rs2 = AccessRuleset(name=u"test2", description=u"fake2")
    node.parents[0].access_ruleset_assocs.append(NodeToAccessRuleset(ruleset=rs1, ruletype="read"))
    node.parents[1].access_ruleset_assocs.append(NodeToAccessRuleset(ruleset=rs2, ruletype="read"))
    effective_rulesets = [assoc.ruleset for assoc in node.effective_access_ruleset_assocs]
    assert rs1 in effective_rulesets
    assert rs2 in effective_rulesets


def test_access_rule_inheritance_read(some_node_with_two_parents):
    s = db.session
    node = some_node_with_two_parents
    rr1 = AccessRule(group_ids=[1])
    rr2 = AccessRule(group_ids=[2])
    rr3 = AccessRule(group_ids=[3])
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rr1, ruletype="read"))
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rr2, ruletype="read"))
    node.parents[1].access_rule_assocs.append(NodeToAccessRule(rule=rr3, ruletype="read"))
    s.flush()
    f = mediatumfunc.update_inherited_access_rules_for_node(node.id)
    s.execute(f)
    assert node.access_rule_assocs.count() == 3


def test_access_rule_inheritance_write(some_node_with_two_parents):
    s = db.session
    node = some_node_with_two_parents
    rw1 = AccessRule(group_ids=[1])
    rw2 = AccessRule(group_ids=[2])
    rw3 = AccessRule(group_ids=[3])
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rw1, ruletype="write"))
    node.parents[0].access_rule_assocs.append(NodeToAccessRule(rule=rw2, ruletype="write"))
    node.parents[1].access_rule_assocs.append(NodeToAccessRule(rule=rw3, ruletype="write"))
    s.flush()
    s.execute(mediatumfunc.update_inherited_access_rules_for_node(node.id))
    assert node.access_rule_assocs.count() == 3


def test_get_or_add_special_access_ruleset(some_node):
    read_ruleset = some_node.get_or_add_special_access_ruleset(u"read")
    assert read_ruleset.description == u"auto-generated"
    assert isinstance(read_ruleset, AccessRuleset)
    assert some_node.access_ruleset_assocs.one().private

    write_ruleset = some_node.get_or_add_special_access_ruleset(u"write")
    assert some_node.access_ruleset_assocs.count() == 2

    same_ruleset_again = some_node.get_or_add_special_access_ruleset(u"write")
    assert same_ruleset_again is write_ruleset


def test_add_another_private_access_ruleset(session, some_node):
    """Private ("special") access rulesets should never be created by hand (use Node.get_or_add_special_access_ruleset).
    But, if you actually do that, this will happen some day:
    """
    with raises(IntegrityError):
        # ok
        some_node.get_or_add_special_access_ruleset(u"read")
        # not ok, someone tries to add a second read private ruleset by hand...
        ruleset = AccessRuleset(name=u"epic_fail")
        ruleset_assoc = NodeToAccessRuleset(ruletype=u"read", ruleset=ruleset, private=True)
        some_node.access_ruleset_assocs.append(ruleset_assoc)
        # flush to enforce constraints
        session.flush()
        
        
def test_filter_read_access(session, guest_user, req, container_node, other_container_node):
    from core import Node
    q = session.query
    
    make_node_public(container_node)
    nodes = q(Node).filter_read_access().all()
    assert len(nodes) == 1
    assert nodes[0] == container_node


def test_filter_read_access_admin(session, admin_user, req, container_node, other_container_node):
    from core import Node
    q = session.query
    session.flush()
    req.session["user_id"] = admin_user.id
    
    nodes = q(Node).filter_read_access().all()
    # admin sees everything, even nodes without any access rights
    assert len(nodes) == 2
    assert container_node in nodes
    assert other_container_node in nodes