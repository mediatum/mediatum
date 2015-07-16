"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>

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

import os
import time
import logging

import core.users as users
from core import config
from core.acl import AccessData
from schema.schema import exportMetaScheme
from utils.utils import getMimeType
from web.services.cache import Cache


logg = logging.getLogger(__name__)

host = "http://" + config.get("host.name")

guestAccess = AccessData(user=users.getUser(u'Gast'))


FILTERCACHE_NODECOUNT_THRESHOLD = 2000000

filtercache = Cache(maxcount=10, verbose=True)
searchcache = Cache(maxcount=10, verbose=True)
resultcache = Cache(maxcount=25, verbose=True)

SEND_TIMETABLE = False


def get_sheme(req, path, params, data, name):

    atime = starttime = time.time()
    r_timetable = []
    userAccess = None

    # get the user and verify the signature
    if params.get('user'):
        # user=users.getUser(params.get('user'))
        #userAccess = AccessData(user=user)
        _user = users.getUser(params.get('user'))
        if not _user:  # user of dynamic

            class dummyuser:  # dummy user class

                def getGroups(self):  # return all groups with given dynamic user
                    return [g.name for g in tree.getRoot('usergroups').getChildren() if g.get(
                        'allow_dynamic') == '1' and params.get('user') in g.get('dynamic_users')]

                def getName(self):
                    return params.get('user')

                def getDirID(self):  # unique identifier
                    return params.get('user')

                def isAdmin(self):
                    return 0

            _user = dummyuser()
        userAccess = AccessData(user=_user)

        if userAccess.user is not None:
            valid = userAccess.verify_request_signature(req.fullpath, params)
            if not valid:
                userAccess = None
        else:
            userAccess = None

    if userAccess is None:
        d = {}
        d['status'] = 'fail'
        d['html_response_code'] = '403'  # denied
        return d['html_response_code'], 0, d

    d = {}
    d['timetable'] = []
    d['status'] = 'ok'
    d['html_response_code'] = '200'  # ok
    d['build_response_end'] = time.time()
    if r_timetable:
        d['timetable'] = r_timetable[:]

    if name.endswith('/'):
        name = name[:-1]
    s = exportMetaScheme(name)

    def compressForDeflate(s):
        import gzip
        return gzip.zlib.compress(s, 9)

    def compressForGzip(s):
        import cStringIO
        import gzip
        buffer = cStringIO.StringIO()
        gzfile = gzip.GzipFile(mode='wb', fileobj=buffer, compresslevel=9)
        gzfile.write(s)
        gzfile.close()
        return buffer.getvalue()

    if 'deflate' in req.params:
        size_uncompressed = len(s)
        compressed_s = compressForDeflate(s)
        s = compressed_s
        size_compressed = len(s)
        try:
            percentage = 100.0 * size_compressed / size_uncompressed
        except:
            percentage = 100.0
        req.reply_headers['Content-Encoding'] = "deflate"
        d['timetable'].append(["'deflate' in request: executed compressForDeflate(s), %d bytes -> %d bytes (compressed to: %.1f %%)" %
                               (size_uncompressed, size_compressed, percentage), time.time() - atime])
        atime = time.time()

    elif 'gzip' in req.params:
        size_uncompressed = len(s)
        compressed_s = compressForGzip(s)
        s = compressed_s
        size_compressed = len(s)
        try:
            percentage = 100.0 * size_compressed / size_uncompressed
        except:
            percentage = 100.0
        req.reply_headers['Content-Encoding'] = "gzip"
        d['timetable'].append(["'gzip' in request: executed compressForGzip(s), %d bytes -> %d bytes (compressed to: %.1f %%)" %
                               (size_uncompressed, size_compressed, percentage), time.time() - atime])
        atime = time.time()

    mimetype = 'text/html'

    req.reply_headers['Content-Type'] = "text/xml; charset=utf-8"
    req.reply_headers['Content-Length'] = len(s)

    req.sendAsBuffer(s, mimetype, force=1)
    d['timetable'].append(["executed req.sendAsBuffer, %d bytes, mimetype='%s'" % (len(s), mimetype), time.time() - atime])
    atime = time.time()
    return d['html_response_code'], len(s), d


def get_app_definitions(req, path, params, data, name):
    return serve_file(req, path, params, data, name + ".xml")


WEBROOT = None


def serve_file(req, path, params, data, filepath):
    atime = starttime = time.time()

    d = {}
    d['timetable'] = []

    if 'mimetype' in req.params:
        mimetype = req.params['mimetype']
    elif filepath.lower().endswith('.html') or filepath.lower().endswith('.htm'):
        mimetype = 'text/html'
    else:
        mimetype = getMimeType(filepath)

    req.reply_headers['Content-Type'] = mimetype

    if WEBROOT:
        basedir = WEBROOT
    else:
        basedir = os.path.dirname(os.path.abspath(__file__))
    abspath = os.path.join(basedir, 'static', filepath)
    logg.info("web service trying to serve: ", abspath)
    if os.path.isfile(abspath):
        filesize = os.path.getsize(abspath)
        req.sendFile(abspath, mimetype, force=1)
        d['timetable'].append(["reading file '%s'" % filepath, time.time() - atime])
        atime = time.time()
        d['status'] = 'ok'
        dataready = "%.3f" % (time.time() - starttime)
        d['dataready'] = dataready
        return 200, filesize, d  # ok
    else:
        d['status'] = 'fail'
        dataready = "%.3f" % (time.time() - starttime)
        d['dataready'] = dataready
        return 404, 0, d  # not found
