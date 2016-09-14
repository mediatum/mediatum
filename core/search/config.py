# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details

Search configuration. Currently, the following language configurations can be set:

* default: used by default in node.search* methods
* service:  used for searches via services (currently: Z39.50, export webservice, OAI)
* fulltext_autoindex: which search configs should be used for automatically indexing fulltexts on changes
* attribute_autoindex: which search configs should be used for automatically indexing attributes on changes

Default value is `simple`. Invalid search configurations are ignored.

`mediatum.cfg` example:

[search]
default_languages=german,english
service_languages=simple
fulltext_autoindex_languages=german,english
attribute_autoindex_languages=german,english,simple


# XXX: maybe we could do that in the database so that an admin could change search parameters at runtime?

"""
from __future__ import absolute_import
import logging
from sqlalchemy import text

from core import config


logg = logging.getLogger(__name__)


default_languages = None
service_languages = None
fulltext_autoindex_languages = None
attribute_autoindex_languages = None


def fts_config_exists(config_name):
    from core import db
    stmt = text("SELECT FROM pg_catalog.pg_ts_config WHERE cfgname = :config_name")
    return db.session.execute(stmt, {"config_name": config_name}).fetchone() is not None


def _get_languages_from_config(key):
    default_languages = set()
    langs_from_config = config.getlist("search." + key, ["simple"])
    for lang in langs_from_config:
        if fts_config_exists(lang):
            default_languages.add(lang)
        else:
            logg.warn("postgres search config '%s' not found, ignored", lang)

    if not default_languages:
        logg.warn("no valid postgres search configs found, using 'simple' config")
        default_languages.add("simple")

    return default_languages


def get_default_search_languages():
    global default_languages
    if not default_languages:
        default_languages = _get_languages_from_config("default_languages")

    return default_languages


def get_service_search_languages():
    global service_languages
    if not service_languages:
        service_languages = _get_languages_from_config("service_languages")

    return service_languages


def get_attribute_autoindex_languages():
    global attribute_autoindex_languages
    if not attribute_autoindex_languages:
        attribute_autoindex_languages = _get_languages_from_config("attribute_autoindex_languages")

    return attribute_autoindex_languages


def get_fulltext_autoindex_languages():
    global fulltext_autoindex_languages
    if not fulltext_autoindex_languages:
        fulltext_autoindex_languages = _get_languages_from_config("fulltext_autoindex_languages")

    return fulltext_autoindex_languages