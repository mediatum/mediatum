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

from schema.schema import Metadatatype
from utils.utils import getMimeType
from core import db
from core.users import user_from_session, get_guest_user, getUser
from core.xmlnode import getNodeXML

import core.oauth as oauth

q = db.query

logg = logging.getLogger(__name__)



def get_sheme(req, path, params, data, name):

    atime = starttime = time.time()
    r_timetable = []
    userAccess = None



    # get the user and verify the signature

    session_user = user_from_session(req.session)

    # get the user and verify the signature
    login_name = params.get('user')
    scheme_name = name

    if login_name:
        user = getUser(login_name)
        if user:
            flag_user_oauth_verified =  oauth.verify_request_signature(
                req.fullpath +
                '?',
                params)
    else:
        flag_user_oauth_verified = False
        user = get_guest_user()
    if user:
        username = user.getName()
    else:
        username = None
    entry_msg = "user: %r, username: %r, session_user: %r, scheme: %r" % (login_name,
                                                                          username,
                                                                          session_user.getName(),
                                                                          scheme_name)
    logg.info("metadata %s" % entry_msg)






    if 0 and not (user and flag_user_oauth_verified):
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

    metadatatype = q(Metadatatype).filter(Metadatatype.name==name).one()
    s = getNodeXML(metadatatype)

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
