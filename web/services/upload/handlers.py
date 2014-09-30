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

import core.tree as tree
import core.users as users
from core import config
from core.acl import AccessData
from utils.date import format_date
from utils.utils import u, getMimeType, OperationException
from utils.fileutils import importFileFromData
from web.services.cache import Cache


logger = logging.getLogger('services')
host = "http://" + config.get("host.name")

collections = tree.getRoot('collections')

FILTERCACHE_NODECOUNT_THRESHOLD = 2000000

filtercache = Cache(maxcount=10, verbose=True)
searchcache = Cache(maxcount=10, verbose=True)
resultcache = Cache(maxcount=25, verbose=True)

SEND_TIMETABLE = False


def upload_new_node(req, path, params, data):

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
    else:
        user = users.getUser('Gast')
        userAccess = AccessData(user=user)

    parent = tree.getNode(params['parent'])

    # check user access
    if userAccess is not None and userAccess.hasAccess(parent, "write"):
        pass
    else:
        s = "No Access"
        req.write(s)
        d = {}
        d['status'] = 'fail'
        d['html_response_code'] = '403'  # forbidden (authorization will not help)
        d['errormessage'] = 'no access'
        return d['html_response_code'], len(s), d

    datatype = params.get('type')
    uploaddir = users.getUploadDir(user)

    n = tree.Node(name=params.get('name'), type=datatype)
    data = base64.b64decode(params.get('data'))
    file = importFileFromData('uploadTest.jpg', data)
    n.addFile(file)

    metadata = json.loads(params.get('metadata'))

    # set provided metadata
    for key, value in metadata.iteritems():
        n.set(u(key), u(value))

    # service flags
    n.set("creator", user.getName())
    n.set("creationtime", format_date())

    parent.addChild(n)

    # process the file, we've added to the new node
    if hasattr(n, "event_files_changed"):
        try:
            n.event_files_changed()

        except OperationException as e:
            for file in n.getFiles():
                if os.path.exists(file.retrieveFile()):
                    os.remove(file.retrieveFile())
            raise OperationException(e.value)

    # make sure the new node is visible immediately from the web service and the search index gets updated
    n.setDirty()
    tree.remove_from_nodecaches(parent)

    d = {}
    d['status'] = 'Created'
    d['html_response_code'] = '201'  # ok
    d['build_response_end'] = time.time()

    s = "Created"

    # provide the uploader with the new node ID
    req.reply_headers['NodeID'] = n.id

    # we need to write in case of POST request, send as buffer wil not work
    req.write(s)

    return d['html_response_code'], len(s), d


def update_node(req, path, params, data, id):

    # get the user and verify the signature
    if params.get('user'):
        user = users.getUser(params.get('user'))
        userAccess = AccessData(user=user)

        if userAccess.user is not None:
            valid = userAccess.verify_request_signature(req.fullpath, params)
            if not valid:
                userAccess = None
        else:
            userAccess = None
    else:
        user = users.getUser('Gast')
        userAccess = AccessData(user=user)

    node = tree.getNode(id)

    # check user access
    if userAccess is not None and userAccess.hasAccess(node, "write"):
        pass
    else:
        s = "No Access"
        req.write(s)
        d = {}
        d['status'] = 'fail'
        d['html_response_code'] = '403'  # forbidden (authorization will not help)
        d['errormessage'] = 'no access'
        return d['html_response_code'], len(s), d

    node.name = params.get('name')

    metadata = json.loads(params.get('metadata'))

    # set provided metadata
    for key, value in metadata.iteritems():
        node.set(u(key), u(value))

    # service flags
    node.set("updateuser", user.getName())
    node.set("updatetime", format_date())
    node.setDirty()

    d = {}
    d['status'] = 'OK'
    d['html_response_code'] = '200'  # ok
    d['build_response_end'] = time.time()

    s = "OK"

    # we need to write in case of POST request, send as buffer wil not work
    req.write(s)

    req.reply_headers['updatetime'] = node.get('updatetime')

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
    msg = "web service trying to serve: " + str(abspath)
    logger.info(msg)
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
