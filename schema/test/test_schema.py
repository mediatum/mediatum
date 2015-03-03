# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

def test_filter_masks(content_node_with_mdt): 
    node = content_node_with_mdt
    masks = node.metadatatype.filter_masks().all()
    assert len(masks) == 4
    

def test_filter_masks_language(content_node_with_mdt): 
    node = content_node_with_mdt
    masks = node.metadatatype.filter_masks(language="en").all()
    # should get english and language-independent masks
    assert len(masks) == 3
    

def test_filter_masks_language_type(content_node_with_mdt): 
    node = content_node_with_mdt
    masks = node.metadatatype.filter_masks(masktype="testmasktype", language="en").all()
    assert len(masks) == 1
    assert masks[0]["masktype"] == "testmasktype"
