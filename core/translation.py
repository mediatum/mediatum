# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import collections as _collections
import os

import backports.functools_lru_cache as _backports_functools_lru_cache
import flask as _flask
import polib as _polib

from mediatumtal import talextracted as _mediatumtal_talextracted

from . import config
from utils.strings import ensure_unicode_returned

_addlangfiles = _collections.defaultdict(list)


class MessageIdNotFound(KeyError):
    pass


@_backports_functools_lru_cache.lru_cache(maxsize=None)
def _parse_po_file_to_dict(po_file_path):
    po = _polib.pofile(po_file_path, encoding='utf-8')
    d = {entry.msgid: entry.msgstr for entry in po.translated_entries()}
    # We currently permit empty strings as messages.
    # However, polib does not expose them in
    # `.translated_entries()`, but in `.untranslated_entries()`.
    # Let's ensure we don't abuse this mechanism.
    for entry in po.untranslated_entries():
        assert entry.msgstr == ""
        d[entry.msgid] = ""
    return d


@_backports_functools_lru_cache.lru_cache(maxsize=None)
def _list_po_files(language):
    plist = []
    i18dir = os.path.join(config.basedir, "i18n")
    lang_ext = "{}.po".format(language)
    for root, dirs, files in os.walk(i18dir, topdown=True):
        for f in files:
            if f.endswith(lang_ext):
                plist.append(os.path.join(i18dir, f))

    plist.extend(filter(os.path.exists, _addlangfiles[language]))

    return tuple(plist)


@ensure_unicode_returned(silent=True)
def translate(language, msgid, mapping={}):
    for pofile in _list_po_files(language):
        po = _parse_po_file_to_dict(pofile)
        if msgid in po:
            return _mediatumtal_talextracted.interpolate(
                po[msgid].encode("utf-8"),
                {k:v.encode("utf-8") for k,v in mapping.iteritems()},
               ).decode("utf-8")

    raise MessageIdNotFound(msgid)


def translate_in_request(msgid, request=None, mapping={}):
    return translate(set_language(request.accept_languages if request else _flask.request.accept_languages), msgid, mapping)


def translate_in_template(msgid, language=None, request=None, mapping={}):
    try:
        if language:
            return translate(language, msgid, mapping)
        else:
            return translate_in_request(msgid, request, mapping)
    except MessageIdNotFound:
        return msgid


def register_po_file(language, path):
    if path not in _addlangfiles[language]:
        _addlangfiles[language].append(path)


def set_language(accept_languages, new_language=None):
    """
    Determine the UI language the user sees.
    Language is picked by following this order of preference:
      1. wish of user, as given in `new_language`
      2. language defined in cookie (set here previously)
      3. language that matches the accept-language http header
      4. our own default language (first configured language)
    The final choice is stored in the session cookie
    *unless* it is equal to the default langauge
    *and* to the accept-language http header.
    It also also stored in `flask.g` for further reference,
    and returned to the function caller.
    """
    if new_language not in config.languages:
        new_language = _flask.session.get("language")
    if new_language not in config.languages:
        new_language = accept_languages.best_match(config.languages)
    if new_language not in config.languages:
        new_language = config.languages[0]
    _flask.session.pop("language", None)
    if new_language != config.languages[0] or new_language != accept_languages.best_match(config.languages):
        _flask.session["language"] = new_language
    return new_language
