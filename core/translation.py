# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from . import config
import os
import stat
import time
import flask as _flask
from utils.locks import named_lock as _named_lock
import codecs
from utils.strings import ensure_unicode_returned


class _POFile:
    filedates = {}

    def __init__(self, filenames):
        self.lock = _named_lock('pofile')
        self.filenames = filenames
        self.map = {}
        self.lastchecktime = None
        for fil in self.filenames:
            self.loadFile(fil)

    def loadFile(self, filename):
        self.filedates[filename] = os.stat(filename)[stat.ST_MTIME]
        self.lastchecktime = time.time()

        with codecs.open(filename, "rb", encoding='utf8') as fi:
            id = None
            for line in fi.readlines():
                if line.startswith("msgid"):
                    id = line[5:].strip()
                    if id[0] == '"' and id[-1] == '"':
                        id = id[1:-1]
                elif line.startswith("msgstr"):
                    text = line[6:].strip()
                    if text[0] == '"' and text[-1] == '"':
                        text = text[1:-1]
                    self.map[id] = text

    def getTranslation(self, key):
        with self.lock:
            if self.lastchecktime + 10 < time.time():
                self.lastchecktime = time.time()
                for fil in self.filenames:
                    if os.stat(fil)[stat.ST_MTIME] != self.filedates[fil]:
                        self.loadFile(fil)
        return self.map[key]

    def addKeys(self, items):
        for item in items:
            if item[0] not in self.map.keys():
                self.map[item[0]] = item[1]

    def addFilename(self, filepath):
        if filepath not in self.filenames:
            self.filenames.append(filepath)

lang2po = {}
addlangitems = {}
addlangfiles = []


@ensure_unicode_returned(silent=True)
def translate(key, language=None, request=None):
    if request and not language:
        language = set_language(request.accept_languages)

    if not request and not language:
        language = set_language(_flask.request.accept_languages)

    if not language:
        return "?%s?" % key

    if language not in lang2po:
        plist = []
        i18dir = os.path.join(config.basedir, "i18n")
        for root, dirs, files in os.walk(i18dir, topdown=True):
            for n in [f for f in files if f.endswith("%s.po" % language)]:
                plist.append(os.path.join(i18dir, n))

        for f in addlangfiles:
            if os.path.exists(f):
                plist.append(f)

        if not plist:
            return key

        lang2po[language] = _POFile(plist)

    try:
        pofile = lang2po[language]
        return pofile.getTranslation(key)
    except KeyError:
        # try additional keys
        try:
            return addlangitems[language][key]
        except KeyError:
            return key


def addLabels(labels):
    for key in labels:
        if key not in addlangitems.keys():
            addlangitems[key] = {}

        for item in labels[key]:
            addlangitems[key][item[0]] = item[1]


def addPoFilepath(filepath=[]):
    for f in filepath:
        if f not in addlangfiles:
            addlangfiles.append(f)


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
