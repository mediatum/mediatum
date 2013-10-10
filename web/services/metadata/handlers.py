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

import sys
import os
import re
import time
import logging

import core.tree as tree
import core.users as users
import core.xmlnode as xmlnode

from core import config
from core.acl import AccessData
from schema.schema import getMetaType, VIEW_DATA_ONLY, exportMetaScheme

from utils.date import format_date
from utils.pathutils import getBrowsingPathList, isDescendantOf
from utils.utils import u, u2, esc, intersection, getMimeType, float_from_gps_format

import web.services.jsonnode as jsonnode
from web.services.rssnode import template_rss_channel, template_rss_item, feed_channel_dict, try_node_date

if sys.version[0:3] < '2.6':
    import simplejson as json
else:
    import json

logger = logging.getLogger('services')
host = "http://" + config.get("host.name")

guestAccess = AccessData(user=users.getUser('Gast'))
collections = tree.getRoot('collections')

from web.services.cache import Cache
from web.services.cache import date2string as cache_date2string
import web.services.serviceutils as serviceutils

FILTERCACHE_NODECOUNT_THRESHOLD = 2000000

filtercache = Cache(maxcount=10, verbose=True)
searchcache = Cache(maxcount=10, verbose=True)
resultcache = Cache(maxcount=25, verbose=True)

SEND_TIMETABLE = False



def get_sheme(req, path, params, data, name):
    
    atime = starttime = time.time()
    r_timetable = []
    userAccess = None
    
    #get the user and verify the signature
    if params.get('user'):
        user=users.getUser(params.get('user'))
        userAccess = AccessData(user=user)
        
        if userAccess.user != None:
            valid = userAccess.verify_request_signature(req.fullpath,params)
            if valid == False:
                userAccess = None
        else:
            userAccess = None
    
    if userAccess == None:
        d = {}
        d['status'] = 'fail'
        d['html_response_code'] = '403' # denied
        return d['html_response_code'], 0, d
    
    d = {}
    d['timetable'] = []
    d['status'] = 'ok'
    d['html_response_code'] = '200' # ok
    d['build_response_end'] = time.time()
    if r_timetable:
        d['timetable'] = r_timetable[:]
        
    s = exportMetaScheme(name)
    

    def compressForDeflate(s):
        import gzip
        return gzip.zlib.compress(s,9)
        
    def compressForGzip(s):
        import cStringIO, gzip
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
        d['timetable'].append(["'deflate' in request: executed compressForDeflate(s), %d bytes -> %d bytes (compressed to: %.1f %%)" % (size_uncompressed, size_compressed, percentage), time.time()-atime]); atime = time.time()

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
        d['timetable'].append(["'gzip' in request: executed compressForGzip(s), %d bytes -> %d bytes (compressed to: %.1f %%)" % (size_uncompressed, size_compressed, percentage), time.time()-atime]); atime = time.time()
    
     
    mimetype = 'text/html'
    
    req.reply_headers['Content-Type'] = "text/xml; charset=utf-8"    
    req.reply_headers['Content-Length'] = len(s)

    req.sendAsBuffer(s, mimetype, force=1)
    d['timetable'].append(["executed req.sendAsBuffer, %d bytes, mimetype='%s'" % (len(s), mimetype), time.time()-atime]); atime = time.time()          
    return d['html_response_code'], len(s), d


def get_app_definitions(req, path, params, data, name):
    return serve_file(req,path,params,data,name+".xml")





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
        basedir = os.path.dirname(os.path.abspath( __file__ ))
    abspath = os.path.join(basedir, 'static', filepath)
    msg = "web service trying to serve: " + str(abspath)
    logger.info(msg)
    if os.path.isfile(abspath):
        filesize = os.path.getsize(abspath)
        req.sendFile(abspath, mimetype, force=1)
        d['timetable'].append(["reading file '%s'" % filepath, time.time()-atime]); atime = time.time()
        d['status'] = 'ok'
        dataready = "%.3f" % (time.time() - starttime)
        d['dataready'] = dataready
        return 200, filesize, d # ok
    else:
        d['status'] = 'fail'
        dataready = "%.3f" % (time.time() - starttime)
        d['dataready'] = dataready        
        return 404, 0, d # not found
