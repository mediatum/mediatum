# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises

from utils.strings import ensure_unicode_returned
from utils.strings import replace_attribute_variables


def test_ensure_unicode_returned_unicode():
    
    @ensure_unicode_returned
    def unicode_function():
        return u"ünicöde-ßtring"
    
    res = unicode_function()
    assert isinstance(res, unicode) 
    
    
def test_ensure_unicode_returned_int(caplog):
    
    @ensure_unicode_returned
    def int_function():
        return 23
    
    res = int_function()
    assert isinstance(res, unicode) 
    log = caplog.records()
    assert len(log) == 1
    assert "int_function" in caplog.text()
    assert log[0].levelname == "WARNING"
    assert "expected unicode, got value of type <type 'int'>" in caplog.text()
    
    
def test_ensure_unicode_returned_utf8_str(caplog):
    
    @ensure_unicode_returned
    def utf8_function():
        return u"ünicöde-ßtring".encode("utf8")
    
    res = utf8_function()
    assert isinstance(res, unicode) 
    log = caplog.records()
    assert len(log) == 1
    assert log[0].levelname == "WARNING"
    assert "utf8_function" in caplog.text()
    assert "expected unicode, trying to decode ustr as utf8" in caplog.text()
    
    
def test_ensure_unicode_returned_custom_name(caplog):
    @ensure_unicode_returned(name="testfunction")
    def noname():
        return 6
    
    noname()
    assert "testfunction" in caplog.text()

    
def test_ensure_unicode_returned_latin_fail(caplog):
    
    @ensure_unicode_returned
    def latin1_function():
        return u"ünicöde-ßtring".encode("latin-1")
    
    with raises(UnicodeDecodeError):
        latin1_function()
    
    log = caplog.records()
    assert len(log) == 1
    assert log[0].levelname == "WARNING"
    assert "latin1_function" in caplog.text()
    assert "expected unicode, trying to decode ustr as utf8" in caplog.text()


def test_replace_attribute_variables_att():
    value = '''test123&lt;att:test_var&gt;blabla;&gt;'''
    nid = 12345
    reg_exp = r"&lt;(.+?)&gt;"
    left_tag = "&lt;"
    right_tag = "&gt;"
    value_getter = lambda attr_name: {'test_var': 'OK', 'x': '---'}.get(attr_name)
    res = replace_attribute_variables(value, nid, value_getter, reg_exp, left_tag, right_tag)
    assert res == u'''test123OKblabla;&gt;'''


def test_replace_attribute_variables_id():
    value = '''test123&lt;att:id&gt;blabla;&gt;'''
    nid = 12345
    reg_exp = r"&lt;(.+?)&gt;"
    left_tag = "&lt;"
    right_tag = "&gt;"
    value_getter = lambda attr_name: {'test_var': 'OK', 'x': '---'}.get(attr_name)
    res = replace_attribute_variables(value, nid, value_getter, reg_exp, left_tag, right_tag)
    assert res == u'''test12312345blabla;&gt;'''


def test_replace_attribute_variables_unicode_val():
    value = '''test123&lt;att:test_var&gt;blabla;&gt;'''
    nid = 12345
    reg_exp = r"&lt;(.+?)&gt;"
    left_tag = "&lt;"
    right_tag = "&gt;"
    value_getter = lambda attr_name: {'test_var': u'äüß', 'x': '---'}.get(attr_name)
    res = replace_attribute_variables(value, nid, value_getter, reg_exp, left_tag, right_tag)
    assert res == u'''test123äüßblabla;&gt;'''


def test_replace_attribute_variables_other_regex():
    value = '''test123<att:test_var>blabla;&gt;'''
    nid = 12345
    reg_exp = r"\<(.+?)\>"
    left_tag = "<"
    right_tag = ">"
    value_getter = lambda attr_name: {'test_var': 'OK', 'x': '---'}.get(attr_name)
    res = replace_attribute_variables(value, nid, value_getter, reg_exp, left_tag, right_tag)
    assert res == u'test123OKblabla;&gt;'
