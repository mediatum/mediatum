# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core import AccessRuleset
from schema.test.factories import MetadatatypeFactory
from web.admin.modules.metatype import add_remove_rulesets_from_metadatatype


def test_add_remove_rulesets_for_metadatatype(session):
    mtype = MetadatatypeFactory()
    rs1 = AccessRuleset(name=u"1")
    rs2 = AccessRuleset(name=u"2")
    session.add(rs1)
    session.add(rs2)
    new_ruleset_names = [u"1"]
    
    add_remove_rulesets_from_metadatatype(mtype, new_ruleset_names)
    assert mtype.access_ruleset_assocs[0].ruleset == rs1
    
    new_ruleset_names = [u"1", u"2"]
    add_remove_rulesets_from_metadatatype(mtype, new_ruleset_names)
    assert {rsa.ruleset for rsa in mtype.access_ruleset_assocs} == set([rs1, rs2])

    new_ruleset_names = [u"2"]
    add_remove_rulesets_from_metadatatype(mtype, new_ruleset_names)
    assert mtype.access_ruleset_assocs[0].ruleset == rs2