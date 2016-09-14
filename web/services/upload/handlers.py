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
import json
import time
import logging
import base64
import types
import re
import hashlib
from collections import OrderedDict

import core.users as users

from core import config

from utils.date import format_date
from utils.utils import u, getMimeType, OperationException
from utils.fileutils import importFileFromData, importFile

from core import Node, db, User
from core.users import user_from_session, get_guest_user, getUser

import core.oauth as oauth

q = db.query
s = db.session

logg = logging.getLogger(__name__)


def upload_new_node(req, path, params, data):

    try:
        uploadfile = params['data']
        del params['data']
    except KeyError:
        uploadfile = None

    session_user = user_from_session(req.session)

    # get the user and verify the signature
    login_name = params.get('user')
    parent_id = int(params.get('parent'))
    datatype = params.get('type')
    try:  # test metadata
        metadata = json.loads(params.get('metadata'))
    except ValueError as e:
        metadata = dict()  # todo: log this

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
    entry_msg = "user: %r, username: %r, session_user: %r, parend_node_id: %r, datatype: %r, metadata: %r" % (login_name,
                                                                                                username,
                                                                                                session_user.getName(),
                                                                                                parent_id,
                                                                                                datatype,
                                                                                                metadata)
    logg.info("upload_new_node %s" % entry_msg)

    parent = q(Node).get(parent_id)
    if not parent:
        logg.info('no such node id: %r' % parent_id)

    # check user access
    if user and flag_user_oauth_verified and parent and parent.has_write_access(user=user):
        pass
    else:
        msg = "No Access"
        req.write(msg)
        d = {
            'status': 'fail',
            'html_response_code': '403',
            'errormessage': 'no access'}
        logg.error("user %r has no edit permission for node %r" % (login_name, parent))
        return d['html_response_code'], len(msg), d


    if isinstance(uploadfile, types.InstanceType):  # file object used
        filename = uploadfile.filename
        nfile = importFile(uploadfile.filename, uploadfile.tempname)

    else:  # string used
        nfile = importFileFromData(
            'uploadTest.jpg',
            base64.b64decode(uploadfile))
        filename = 'uploadTest.jpg'

    mimetype = getMimeType(filename)
    typestring = mimetype[1]

    if '/' in datatype:
        typestring, schemastring = datatype.rplit('/', 1)  # override mimetype by user input
    else:
        schemastring = datatype
        # todo: check user access to this schema

    try:
        content_class = Node.get_class_for_typestring(typestring)
        n = content_class(name=filename, schema=schemastring)
    except Exception as e:
        msg = "failed to create node of type %r and schema %r" % (typestring, schemastring)
        req.write(msg)
        logg.exception(msg)
        d = {
            'status': 'fail',
            'html_response_code': '403',
            'errormessage': 'no access'}
        return d['html_response_code'], len(msg), d

    parent.children.append(n)

    # set provided metadata
    for key, value in metadata.iteritems():
        n.set(u(key), u(value))

    # service flags
    n.set("creator", user.getName())
    n.set("creationtime", format_date())

    db.session.commit()

    try:
        n_id = n.id
    except:
        n_id = None

    if nfile:
        n.files.append(nfile)
    else:
        logg.error("error in file uploadservice")

    db.session.commit()

    try:
        n.event_files_changed()
    except:
        for file_to_delete in n.getFiles():
            if os.path.exists(file_to_delete.retrieveFile()):
                os.remove(file_to_delete.retrieveFile())
        raise

    d = {
        'status': 'Created',
        'html_response_code': '201',
        'build_response_end': time.time()}

    msg = "Created"

    # provide the uploader with the new node ID
    req.reply_headers['NodeID'] = str(n_id)

    # we need to write in case of POST request, send as buffer will not work
    req.write(msg)

    logg.info("upload_new_node: OK %s" % entry_msg)

    return d['html_response_code'], len(msg), d


def update_node(req, path, params, data, id):

    # get the user and verify the signature

    session_user = user_from_session(req.session)

    # get the user and verify the signature
    login_name = params.get('user')
    node_name = params.get('name')
    try:  # test metadata
        metadata = json.loads(params.get('metadata'))
    except ValueError as e:
        metadata = dict()  # todo: log this

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
    entry_msg = "user: %r, username: %r, session_user: %r, node_id: %r, node_name: %r, metadata: %r" % (login_name,
                                                                                        username,
                                                                                        session_user.getName(),
                                                                                        id,
                                                                                        node_name,
                                                                                        metadata)
    logg.info("update_node %s" % entry_msg)

    node = q(Node).get(id)
    if not node:
        logg.info('no such node id: %r' % id)

    # check user access
    if user and flag_user_oauth_verified and node and node.has_write_access(user=user):
        pass
    else:
        msg = "No Access"
        req.write(msg)
        d = {
            'status': 'fail',
            'html_response_code': '403',
            'errormessage': 'no access'}
        logg.error("user %r has no edit permission for node %r" % (login_name, node))
        return d['html_response_code'], len(msg), d

    node.name = node_name

    # XXX: set legacy update attributes
    metadata["updateuser"] = user.getName()
    metadata["updatetime"] = format_date()

    node.attrs.update(metadata)
    
    db.session.commit()

    d = {
        'status': 'OK',
        'html_response_code': '200',
        'build_response_end': time.time()}
    s = "OK"

    # we need to write in case of POST request, send as buffer wil not work
    req.write(s)

    req.reply_headers['updatetime'] = node.updatetime

    logg.info("update_node: OK %s" % entry_msg)

    return d['html_response_code'], len(s), d

# alternative base dir for static html files
#
# relative to mediatum folder:
# WEBROOT="./web/services/static01/files/"
#
# absolute:
# WEBROOT="/tmp/"

# WEBROOT="./web/services/static01/files/"

# no WEBROOT configured, default will be used
WEBROOT = None


def serve_file(req, path, params, data, filepath):
    atime = starttime = time.time()

    d = {'timetable': []}
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
    logg.info("web service trying to serve: %s", abspath)
    if os.path.isfile(abspath):
        filesize = os.path.getsize(abspath)
        req.sendFile(abspath, mimetype, force=1)
        d['timetable'].append(
            ["reading file '%s'" % filepath, time.time() - atime])
        d['status'] = 'ok'
        d['dataready'] = "%.3f" % (time.time() - starttime)
        return 200, filesize, d  # ok
    else:
        d['status'] = 'fail'
        d['dataready'] = "%.3f" % (time.time() - starttime)
        return 404, 0, d  # not found


def calcsign(req, path, params, data):
    s = "OK"
    url = OrderedDict()

    for key in re.split('\?|\&', req.params.get('url')):
        k = key.split('=')
        if len(k) < 2:
            k.append('')
        url[k[0]] = k[1]

    teststring = "/services/upload/new?"
    for k in sorted(url.keys()[1:]):
        teststring += '%s=%s&' % (k, url[k])
    if 'key' in params:
        teststring = "%s%s" % (params['key'], teststring)

    h = hashlib.md5()
    h.update(teststring[:-1])
    req.write(h.hexdigest())
    return 200, len(s), {}
