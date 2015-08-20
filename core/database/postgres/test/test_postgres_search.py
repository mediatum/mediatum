# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Postgres-specific search tests
"""

import core
from core.database.postgres.search import _prepare_searchstring

def test_search_config_nothing(monkeypatch):
    import core.database.postgres.search
    monkeypatch.setattr(core.database.postgres.search, "config", {})
    from core.database.postgres.search import default_languages_from_config
    langs = default_languages_from_config()
    assert langs == set(["simple"])


def test_search_config_wrong(monkeypatch):
    import core.database.postgres.search
    monkeypatch.setattr(core.database.postgres.search, "config", {"search.default_languages": "invalid"})
    from core.database.postgres.search import default_languages_from_config
    langs = default_languages_from_config()
    assert langs == set(["simple"])


def test_search_config(monkeypatch):
    import core.database.postgres.search
    monkeypatch.setattr(core.database.postgres.search, "config", {"search.default_languages": "english,dutch"})
    from core.database.postgres.search import default_languages_from_config
    langs = default_languages_from_config()
    assert langs == set(["english", "dutch"])


def test_prepare_searchstring_simple():
    searchstring = u' "python"  '
    res = _prepare_searchstring("|", searchstring)
    assert res == u"python"


def test_prepare_searchstring_or():
    searchstring = u'python nim scala'
    res = _prepare_searchstring("|", searchstring)
    assert res == u"python|nim|scala"


def test_prepare_searchstring_or_prefix():
    searchstring = u'pyth* ni* sca*'
    res = _prepare_searchstring("|", searchstring)
    assert res == u"pyth:*|ni:*|sca:*"
