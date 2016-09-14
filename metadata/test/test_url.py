# -*- coding: utf-8 -*-
'''
Created on 06.08.2013
@author: stenzel
'''
from __future__ import division, absolute_import
import os.path
from mock import MagicMock
import pytest

from metadata import url

BASEDIR = os.path.join(os.path.dirname(__file__), "test_data")


@pytest.fixture
def m():
    return url.m_url()

Field = MagicMock(name="field")


@pytest.fixture
def field():
    field = Field()
    field.getValues.return_value = "\r\n"
    field.getName.return_value = "www-address"
    return field

Node = MagicMock(name="node")


@pytest.fixture
def node():
    node = Node()
    node.get.return_value = "http://dx.doi.org/10.1002/%28SICI%291522-2594%28199911%2942%3A5%3C952%3A%3AAID-MRM16%3E3.0.CO%3B2-S;Name"
    return node


def test_get_formated_value(m, node, field):
    assert isinstance(m, url.m_url)
    ret = m.getFormattedValue(field, node)
    expected = '<a href="http://dx.doi.org/10.1002/%28SICI%291522-2594%28199911%2942%3A5%3C952%3A%3AAID-MRM16%3E3.0.CO%3B2-S" target="_blank" title="?show in new window?">Name</a>'
    assert ret[1] == expected
    return ret


def test_format_request_value_for_db(m, field):
    assert isinstance(m, url.m_url)
    params = {
        u"www-address": u"http://dx.doi.org/10.1002/(SICI)1522-2594(199911)42:5<952::AID-MRM16>3.0.CO;2-S",
        u"www-address_text": u"Link with ; inside"
    }
    ret = m.format_request_value_for_db(field, params, "www-address")
    expected = u"http://dx.doi.org/10.1002/%28SICI%291522-2594%28199911%2942%3A5%3C952%3A%3AAID-MRM16%3E3.0.CO%3B2-S;Link with \u037e inside"
    assert ret == expected
    return ret


def test_format_request_value_for_db_umlaut(m, field):
    assert isinstance(m, url.m_url)
    params = {
        u"www-address": u"http://dx.doi.org/10.1002/(SICI)1522-2594(199911)42:5<952::AID-MRM16>3.0.CO;2-S",
        u"www-address_text": u"Irgendwäß mit Ümlauten."
    }
    ret = m.format_request_value_for_db(field, params, "www-address")
    expected = u"http://dx.doi.org/10.1002/%28SICI%291522-2594%28199911%2942%3A5%3C952%3A%3AAID-MRM16%3E3.0.CO%3B2-S;Irgendwäß mit Ümlauten."
    assert ret == expected
    return ret


if __name__ == "__main__":
    print "test_get_formated_value", test_get_formated_value(m(), node(), field())
    print "test_format_request_value_for_db", test_format_request_value_for_db(m(), field())
