# -*- coding: utf-8 -*-
'''
Created on 22.07.2013
@author: stenzel

XXX: These tests are database dependent. They only work when the DB is prepared for that. They also change the DB!
WARNING: Don't run them on production databases...
'''
from __future__ import division, absolute_import
import json
import os.path
from pytest import raises

from core import tree
from .. import citeproc
from ..citeproc import get_citeproc_json, DOINotFound, FIELDS, CSLField
from ..importbase import NoMappingFound

BASEDIR = os.path.join(os.path.dirname(__file__), "test_data")
DOI_ARTICLE = "10.1038/nphys1170"
DOI_BOOK = "10.1007/3-540-44895-0_1"
DOI_UTF8 = "10.1007/978-3-540-69073-3_6"


def _get_path(doi, typ):
    filename = doi.replace("/", "_slash_") + "." + typ
    return os.path.join(BASEDIR, filename)

 
def test_get_citeproc_json_article():
    expected = json.load(open(_get_path(DOI_ARTICLE, "json")))
    res = get_citeproc_json(DOI_ARTICLE)
    assert expected == res
 
 
def test_get_citeproc_json_fail():
    with raises(DOINotFound):
        get_citeproc_json("invalid")
         
         
def test_fields():
    standard_field = FIELDS["abstract"]
    assert isinstance(standard_field, CSLField)
    assert standard_field.fieldtype == "standard"
    date_field = FIELDS["issued"]
    assert isinstance(date_field, CSLField)
    assert date_field.fieldtype == "date"
     
    
def test_import_doi():
    target = tree.Node("test", "directory")
    node = citeproc.import_doi(DOI_BOOK, target)
    assert isinstance(node, tree.Node)
    print(node.id)
    
    
def test_import_doi_utf8():
    target = tree.Node("test", "directory")
    node = citeproc.import_doi(DOI_UTF8, target)
    assert isinstance(node, tree.Node)
    print(node.id)
    
def test_get_citeproc_no_mapping():
    with raises(NoMappingFound):
        citeproc.import_doi(DOI_ARTICLE, None)
 