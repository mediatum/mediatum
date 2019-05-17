# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.translation import set_language
import core


def test_set_language_default_one(monkeypatch, req):
    monkeypatch.setattr(core.config, "languages", ["en"])
    assert set_language(req) == "en"
    
    
def test_set_language_default_multiple(monkeypatch, req):
    monkeypatch.setattr(core.config, "languages", ["en", "de"])
    assert set_language(req) == "en"
    
    
def test_set_language_accept_header(monkeypatch, req):
    req.headers["accept-language"] = "de,en;q=0.5"
    monkeypatch.setattr(core.config, "languages", ["en", "de"])
    assert set_language(req) == "de"
    
    
def test_set_language_accept_header_not_accepted(monkeypatch, req):
    req.headers["accept-language"] = "no"
    monkeypatch.setattr(core.config, "languages", ["en", "de"])
    assert set_language(req) == "en"


def test_set_language_cookie(monkeypatch, req):
    req.cookies["language"] = "de"
    monkeypatch.setattr(core.config, "languages", ["en", "de"])
    assert set_language(req) == "de"


def test_set_language_cookie_not_accepted(monkeypatch, req):
    req.cookies["language"] = "no"
    monkeypatch.setattr(core.config, "languages", ["en", "de"])
    assert set_language(req) == "en"