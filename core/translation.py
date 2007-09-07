"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
import config
from utils.utils import join_paths
import os
import stat
import time
import thread

class _POFile:
    def __init__(self,filename): 
        self.lock = thread.allocate_lock()
        self.filename=filename
        self.loadFile(filename)

    def loadFile(self,filename):
        self.filedate=os.stat(self.filename)[stat.ST_MTIME]
        self.lastchecktime=time.time()
        self.map = {}
        fi = open(filename, "rb")
        id = None
        for line in fi.readlines():
            if line.startswith("msgid"):
                id = line[5:].strip()
                if id[0] == '"' and id[-1]=='"':
                    id = id[1:-1]
            elif line.startswith("msgstr"):
                text = line[6:].strip()
                if text[0] == '"' and text[-1]=='"':
                    text = text[1:-1]
                self.map[id] = text
        fi.close()

    def getTranslation(self,key):
        self.lock.acquire()
        try:
            if self.lastchecktime + 10 < time.time():
                self.lastchecktime = time.time()
                if os.stat(self.filename)[stat.ST_MTIME] != self.filedate:
                    self.loadFile(self.filename)
        finally:
            self.lock.release()
        return self.map[key]

lang2po = {}

def translate(key, language=None, request=None):
    if request and not language:
        language = lang(request)

    if not language:
        return "?"+key+"?"
   
    if language not in lang2po:
        filename = config.get("i18n."+language)
        if not filename:
            return key
        lang2po[language] = _POFile(join_paths(config.basedir,config.get("i18n."+language)))

    try:
        pofile = lang2po[language]
        return pofile.getTranslation(key)
    except KeyError:
       return key

def lang(req):
    if "language" in req.params and req.params["language"]:
        req.session["language"] = req.params["language"]
        return req.session["language"]
    elif "language" in req.session and req.session["language"]:
        return req.session["language"]

    allowed_languages = config.get("i18n.languages","en").split(",")
    if "Accept-Language" in req.request_headers:
        languages = req.request_headers["Accept-Language"]
        for language in languages.split(";"):
            if language and language in allowed_languages:
                req.session["language"] = language
                return language
    if allowed_languages and allowed_languages[0]:
        req.session["language"] = allowed_languages[0]
        return allowed_languages[0]
    else:
        return "en"

def switch_language(req, language):
    allowed_languages = config.get("i18n.languages","en").split(",")
    if language not in allowed_languages:
        raise "Language "+language+" not configured"
    req.session["language"] = language

def t(target,key):
    if type(target) == type(""):
        return translate(key,language=target)
    else:
        return translate(key,request=target)

def getDefaultLanguage():
    return config.get("i18n.languages").split(",")[0]
