# -*- coding: utf-8 -*-
'''
Created on 22.07.2013
@author: stenzel
'''
from __future__ import division, absolute_import
import json
import os.path
import datetime
from pprint import pprint
from pytest import raises, mark

from core import Node, db
from utils.compat import iteritems
from .. import citeproc
from ..citeproc import get_citeproc_json, DOINotFound, FIELDS, CSLField


BASEDIR = os.path.join(os.path.dirname(__file__), "test_data")
DOI_ARTICLE = "10.1038/nmat3712"
DOI_ARTICLE2 = "10.1038/nphys1170"
DOI_ARTICLE3 = "10.1016/j.susc.2010.09.012"
DOI_BOOK = "10.1007/3-540-44895-0_1"
DOI_UTF8 = "10.1007/978-3-540-69073-3_6"
DOI_MISC = "10.1594/PANGAEA.726855"
DOI_LITERAL_AUTHOR_RAW_DATE = "10.5284/1021188"


def load_csl_record_file(doi):
    fn = doi.replace("/", "_slash_") + ".json"
    fp = os.path.join(BASEDIR, fn)
    return json.load(open(fp))


def check_node(node, expected, **check_attrs):
    assert isinstance(node, Node)
    print("expected node content:")
    pprint(expected)
    print("actual node attributes:")
    pprint(node.attributes)
    # every doi-imported node must fulfill this
    assert node.name == expected[u"DOI"]
    doi = node.get(u"doi") or node.get(u"DOI")
    assert doi == expected[u"DOI"]
    # additional attribute value checks
    for attr, expected in iteritems(check_attrs):
        value = node.get(attr)
        if value:
            assert value == expected


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



def test_convert_raw_date():
    year = 2023
    date_value = {u"raw": unicode(year)}
    dat = citeproc.convert_csl_date(date_value)
    assert dat == datetime.date(year=year, month=1, day=1).isoformat()


def test_convert_date_parts():
    year = 2003
    month = 5
    day = 27
    date_value = {u"date-parts": [[year, month, day]]}
    dat = citeproc.convert_csl_date(date_value)
    assert dat == datetime.date(year=year, month=month, day=day).isoformat()


def test_fields():
    standard_field = FIELDS["abstract"]
    assert isinstance(standard_field, CSLField)
    assert standard_field.fieldtype == "standard"
    date_field = FIELDS["issued"]
    assert isinstance(date_field, CSLField)
    assert date_field.fieldtype == "date"


def test_import_csl(journal_article_mdt):
    """Test importing a local CSL file"""
    record = load_csl_record_file(DOI_ARTICLE)
    node = citeproc.import_csl(record, testing=True)
    # check if database can serialize the contents
    db.session.add(node)
    db.session.flush()
    check_node(node, record,
               issued=datetime.date(year=2013, month=7, day=21).isoformat())


def test_import_csl_utf8(journal_article_mdt):
    """Test importing a local CSL file with non-ASCII characters"""
    record = load_csl_record_file(DOI_UTF8)
    node = citeproc.import_csl(record, testing=True)
    check_node(node, record,
               author=u"Weisemöller, Ingo;Schürr, Andy")


@mark.slow
def test_import_doi(journal_article_mdt):
    """Note: this contacts the real citeproc server. Marked as slow because of that."""
    node = citeproc.import_doi(DOI_UTF8, testing=True)
    expected = load_csl_record_file(DOI_UTF8)
    # check if database can serialize the contents
    db.session.add(node)
    db.session.flush()
    check_node(node, expected)

