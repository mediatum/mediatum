# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Postgres-specific search tests
"""

import core

def test_search_config_nothing(monkeypatch):
    monkeypatch.setattr(core, "config", {})
    from core.database.postgres.search import default_languages_from_config
    langs = default_languages_from_config()
    assert langs == set(["simple"])


def test_search_config_wrong(monkeypatch):
    monkeypatch.setattr(core, "config", {"search.default_languages": "invalid"})
    from core.database.postgres.search import default_languages_from_config
    langs = default_languages_from_config()
    assert langs == set(["simple"])


def test_search_config(monkeypatch):
    import core.database.postgres.search
    monkeypatch.setattr(core.database.postgres.search, "config", {"search.default_languages": "english,german"})
    from core.database.postgres.search import default_languages_from_config
    langs = default_languages_from_config()
    assert langs == set(["german", "english"])

