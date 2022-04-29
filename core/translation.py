# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import collections as _collections
import os

import backports.functools_lru_cache as _backports_functools_lru_cache
import flask as _flask
import polib as _polib

from . import config
from utils.strings import ensure_unicode_returned

_addlangitems = {}
_addlangfiles = _collections.defaultdict(list)


@_backports_functools_lru_cache.lru_cache(maxsize=None)
def _parse_po_file_to_dict(po_file_path):
    po = _polib.pofile(po_file_path, encoding='utf-8')
    return {entry.msgid: entry.msgstr for entry in po.translated_entries()}


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


def _translate_lang_and_key_to_translated_text(language, msg_id):
    for pofile in _list_po_files(language):
        po = _parse_po_file_to_dict(pofile)
        if msg_id in po:
            return po[msg_id]


@ensure_unicode_returned(silent=True)
def translate(msg_id, language=None, request=None):
    if request and not language:
        language = set_language(request.accept_languages)

    if not request and not language:
        language = set_language(_flask.request.accept_languages)

    if not language:
        return "?{}?".format(msg_id)

    msg_str = _translate_lang_and_key_to_translated_text(language, msg_id)
    if msg_str:
        return msg_str

    # try additional keys
    try:
        return _addlangitems[language][msg_id]
    except KeyError:
        return msg_id


def addLabels(labels):
    for key in labels:
        if key not in _addlangitems.keys():
            _addlangitems[key] = {}

        for item in labels[key]:
            _addlangitems[key][item[0]] = item[1]


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


def t(target, key):
    if isinstance(target, basestring):
        return translate(key, language=target)
    else:
        return translate(key, request=target)
