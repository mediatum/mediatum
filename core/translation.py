"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Peter Heckl <heckl@ub.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from . import config
import os
import stat
import time
import flask as _flask
from utils.locks import named_lock as _named_lock
import codecs
from utils.strings import ensure_unicode_returned
from werkzeug import parse_accept_header, LanguageAccept
from core.request_handler import get_header as _get_header
from core.request_handler import setCookie as _setCookie


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
        language = lang(request)

    if not request and not language:
        language = lang(_flask.request)

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


def addLabels(labels={}):
    for key in labels:
        if key not in addlangitems.keys():
            addlangitems[key] = {}

        for item in labels[key]:
            addlangitems[key][item[0]] = item[1]


def addPoFilepath(filepath=[]):
    for f in filepath:
        if f not in addlangfiles:
            addlangfiles.append(f)


def lang(req):
    # simple cache, lang won't change in the current request
    if hasattr(req, "_lang"):
        return req._lang
    
    return set_language(req)

    
def set_language(req):
    allowed_languages = config.languages

    language_from_cookie = req.cookies.get("language")
    if language_from_cookie in allowed_languages:
        req._lang = language_from_cookie
        return language_from_cookie

    language = allowed_languages[0]
    
    accept_languages_header = _get_header(req, "Accept-Language")
    accept_languages = parse_accept_header(accept_languages_header, cls=LanguageAccept)
    best_match = accept_languages.best_match(allowed_languages)
    
    if best_match:
        language = best_match
    
    if language != default_language:
        _setCookie(req, "language", language, path="/")
    
    req._lang = language
    return language


def switch_language(req, language):
    allowed_languages = config.languages
    if language is None and len(allowed_languages) > 0:
        language = allowed_languages[0]
    elif language not in allowed_languages:
        language = allowed_languages[0]
    _setCookie(req, "language", language, path="/")


def t(target, key):
    if isinstance(target, basestring):
        return translate(key, language=target)
    else:
        return translate(key, request=target)


# XXX: cache the default language, we assume that the config doesn't change at runtime
global default_language
default_language = None


def getDefaultLanguage():
    global default_language

    if default_language is None:
        default_language = config.languages[0]

    return default_language
