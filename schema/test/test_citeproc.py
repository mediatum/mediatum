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
import logging as logg
logg.basicConfig()
from pprint import pprint
from pytest import raises, fixture

from core import tree
from .. import citeproc
from ..citeproc import get_citeproc_json, DOINotFound, FIELDS, CSLField
from ..importbase import NoMappingFound

BASEDIR = os.path.join(os.path.dirname(__file__), "test_data")
DOI_ARTICLE = "10.1038/nmat3712"
DOI_ARTICLE2 = "10.1038/nphys1170"
DOI_ARTICLE3 = "10.1016/j.susc.2010.09.012"
DOI_BOOK = "10.1007/3-540-44895-0_1"
DOI_UTF8 = "10.1007/978-3-540-69073-3_6"
DOI_MISC = "10.1594/PANGAEA.726855"

def load_csl_record_file(doi):
    fn = doi.replace("/", "_slash_") + ".json"
    fp = os.path.join(BASEDIR, fn)
    return json.load(open(fp))


@fixture
def target():
    return tree.Node("test", "directory")


def check_node(node, expected):
    assert isinstance(node, tree.Node)
    print("expected node content:")
    pprint(expected)
    print("actual node attributes:")
    pprint(node.attributes)
    if expected:
        doi = node.get("doi") or node.get("DOI")
        assert doi == expected["DOI"]
        publisher = node.get("publisher")
        assert publisher == expected["publisher"]


def _get_path(doi, typ):
    filename = doi.replace("/", "_slash_") + "." + typ
    return os.path.join(BASEDIR, filename)


def test_get_citeproc_json_article():
    expected = load_csl_record_file(DOI_ARTICLE)
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


def test_import_csl(target):
    record = load_csl_record_file(DOI_ARTICLE)
    node = citeproc.import_csl(record, target)
    check_node(node, record)


def test_import_doi(target):
    node = citeproc.import_doi(DOI_ARTICLE3, target)
    expected = load_csl_record_file(DOI_ARTICLE3)
    check_node(node, expected)


def test_import_doi_utf8(target):
    node = citeproc.import_doi(DOI_UTF8, target)
    expected = load_csl_record_file(DOI_UTF8)
    check_node(node, expected)


def test_get_citeproc_no_mapping():
    with raises(NoMappingFound):
        citeproc.import_doi(DOI_MISC, target=None)
