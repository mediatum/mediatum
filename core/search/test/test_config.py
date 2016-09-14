# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import core.config
import core.search.config as searchconfig
from core.search.config import get_default_search_languages, get_service_search_languages, get_fulltext_autoindex_languages,\
    get_attribute_autoindex_languages

# Warning: get_*languages() functions cache their value, so it must be reset before testing

def test_default_search_config_nothing(monkeypatch, session):
    monkeypatch.setattr(core.config, "settings", {})
    # the getter caches the value, so we must reset is first
    searchconfig.default_languages = None
    langs = get_default_search_languages()
    assert langs == set(["simple"])


def test_default_search_config_wrong(monkeypatch, session):
    monkeypatch.setattr(core.config, "settings", {"search.default_languages": "invalid"})
    searchconfig.default_languages = None
    langs = get_default_search_languages()
    assert langs == set(["simple"])


def test_default_search_config_value_given(monkeypatch, session):
    monkeypatch.setattr(core.config, "settings", {"search.default_languages": "english, dutch"})
    searchconfig.default_languages = None
    langs = get_default_search_languages()
    assert langs == set(["english", "dutch"])


def test_service_search_config_value_given(monkeypatch, session):
    monkeypatch.setattr(core.config, "settings", {"search.service_languages": "simple, english"})
    searchconfig.service_languages = None
    langs = get_service_search_languages()
    assert langs == set(["simple", "english"])


def test_fulltext_autoindex_languages_value_given(monkeypatch, session):
    monkeypatch.setattr(core.config, "settings", {"search.fulltext_autoindex_languages": "english, dutch"})
    searchconfig.fulltext_autoindex_languages = None
    langs = get_fulltext_autoindex_languages()
    assert langs == set(["english", "dutch"])


def test_attribute_autoindex_languages_value_given(monkeypatch, session):
    monkeypatch.setattr(core.config, "settings", {"search.attribute_autoindex_languages": "simple, english"})
    searchconfig.attribute_autoindex_languages = None
    langs = get_attribute_autoindex_languages()
    assert langs == set(["simple", "english"])