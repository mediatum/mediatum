# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises

from utils.strings import ensure_unicode_returned


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
    