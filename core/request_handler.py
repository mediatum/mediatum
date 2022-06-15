# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import datetime as _datetime
import re as _re
import os as _os
import stat as _stat
import string as _string
import logging as _logging
import mimetypes as _mimetypes
import importlib as _importlib
from cgi import escape as _escape
from functools import partial as _partial

import flask as _flask

import core.translation as _core_translation
import httpstatus as _httpstatus
from core import config as _config
from utils import utils as _utils_utils
from utils.url import build_url_from_path_and_params as _build_url_from_path_and_params
from collections import OrderedDict as _OrderedDict

_logg = _logging.getLogger(__name__)

_basedir = "no-root-dir-set"

contexts = []
global_modules = {}

BASENAME = _re.compile("([^/]*/)*([^/.]*)(.py)?")


def qualify_path(p):
    if p[-1] != '/':
        return p + "/"
    return p


def setBase(base):
    global _basedir
    _basedir = qualify_path(base)


class _WebFile:

    def __init__(self, context, filename, module=None):
        self.context = context
        if filename[0] == '/':
            filename = filename[1:]
        self.filename = filename
        if module is None:
            self.m = _load_module(_utils_utils.join_paths(context.root, filename))
        else:
            self.m = module
            global_modules[filename] = module
        self.handlers = []

    def addHandler(self, function):
        handler = _WebHandler(self, function)
        self.handlers += [handler]
        return handler

    def getFileName(self):
        return self.context.root + self.filename


class _WebHandler:

    def __init__(self, file, function):
        self.file = file
        if isinstance(function, str):
            self.function = function
            m = file.m
            with _utils_utils.nullcontext():
                self.f = getattr(m, function)
        else:
            self.f = function
            self.function = function.func_name

    def addPattern(self, pattern):
        p = _WebPattern(self, pattern)
        desc = "pattern %s, file %s, function %s" % (pattern, self.file.filename, self.function)
        self.file.context.pattern_to_function[p.getPattern()] = (self.f, desc)
        return p


class _WebPattern:

    def __init__(self, handler, pattern):
        self.handler = handler
        self.pattern = pattern
        if not pattern.endswith('$'):
            pattern = pattern + "$"
        self.compiled = _re.compile(pattern)

    def getPattern(self):
        return self.compiled

    def getPatternString(self):
        return self.pattern


class _OSFilesystem:
    # set this to zero if you want to disable pathname globbing.
    # [we currently don't glob, anyway]
    def __init__(self, root):
        self.root = root

    def isfile(self, path):
        p = self.normalize(_os.path.join("/", path))
        return _os.path.isfile(self.translate(p))

    def isdir(self, path):
        p = self.normalize(_os.path.join("/", path))
        return _os.path.isdir(self.translate(p))

    # TODO: implement a cache w/timeout for stat()
    def stat(self, path):
        p = self.translate(path)
        return _os.stat(p)

    def open(self, path, mode):
        p = self.translate(path)
        return open(p, mode)

    # utility methods
    def normalize(self, path):
        # watch for the ever-sneaky '/+' path element
        path = _re.sub('/+', '/', path)
        p = _os.path.normpath(path)
        # remove 'dangling' cdup's.
        if len(p) > 2 and p[:3] == '/..':
            p = '/'
        return p

    def translate(self, path):
        # we need to join together three separate
        # path components, and do it safely.
        # <real_root>/<current_directory>/<path>
        # use the operating system's path separator.
        path = _string.join(_string.split(path, '/'), _os.sep)
        p = self.normalize(_os.path.join('/', path))
        p = self.normalize(_os.path.join(self.root, p[1:]))
        return p


def sendFile(req, path, content_type, force=0):
    assert req.method == 'GET'
    if isinstance(path, unicode):
        path = path.encode("utf8")

    _logg.debug("sendFile: %s", path)

    assert _os.path.isabs(path), "sendFile: path: {} is not an absolute path".format(path)

    # TODO: It should be checked if a path is a subdirectory of another path.
    #       This would be a configuration error by the admin.
    for nginx_alias, nginx_dir in _config.getsubset("nginx-redirect").iteritems():
        assert _os.path.isabs(nginx_dir), "sendFile: nginx_dir: {} is not an absolute path".format(nginx_dir)
        if not _os.path.relpath(path, nginx_dir).startswith("../"):
            break
    else:
        nginx_alias = None

    try:
        mtime = _datetime.datetime.utcfromtimestamp(_os.stat(path)[_stat.ST_MTIME])
    except OSError:
        req.response.status_code = _httpstatus.HTTP_NOT_FOUND
        return

    if req.if_modified_since and mtime <= req.if_modified_since and not force:
        req.response.status_code = 304
        return

    if not nginx_alias:
        req.response = _flask.send_file(path, conditional=True)
        return

    if isinstance(content_type, unicode):
        content_type = content_type.encode("utf8")
    req.response.last_modified = mtime
    req.response.content_type = content_type
    req.response.headers['X-Accel-Redirect'] = _os.path.join("/{}".format(nginx_alias), _os.path.relpath(path, nginx_dir))


def makeSelfLink(req, params):
    params2 = req.params.copy()
    for k, v in params.items():
        if v is not None:
            params2[k] = v
        else:
            with _utils_utils.suppress(Exception, warn=False):
                del params2[k]
    ret = _build_url_from_path_and_params(req.path, params2)
    return ret


# COMPAT: added functions


def _load_module(filename):
    b = BASENAME.match(filename)

    # filename e.g. /my/modules/test.py
    # b.group(1) = /my/modules/
    # b.group(2) = test.py
    if b is None:
        raise ValueError("Internal error with filename " + filename)
    module = b.group(2)
    if module is None:
        raise ValueError("Internal error with filename " + filename)

    while filename.startswith("./"):
        filename = filename[2:]

    if filename in global_modules:
        return global_modules[filename]

    dir = _os.path.dirname(filename)
    path = dir.replace("/", ".")

    # strip tailing/leading dots
    while len(path) and path[0] == '.':
        path = path[1:]
    while len(path) and path[-1] != '.':
        path = path + "."

    module2 = (path + module)
    _logg.debug("Loading module %s", module2)

    m = _importlib.import_module(module2)
    global_modules[filename] = m
    return m


class _WebContext:

    def __init__(self, name, root=None):
        self.name = name
        self.files = []
        self.startupfile = None
        if root:
            self.root = qualify_path(root)
        self.pattern_to_function = _OrderedDict()
        self.catchall_handler = None

    def addFile(self, filename, module=None):
        file = _WebFile(self, filename, module)
        self.files += [file]
        return file

    def match(self, path):
        def call_and_close(f, req):
            status = f(req)
            if type("1") == type(status):
                status = int(status)
            if status is not None and type(1) == type(status) and status > 10:
                req.response.status_code = status
                if(status >= 400 and status <= 500):
                    req.response.status_code = status
                    req.response.set_data(_httpstatus.responses[status])
                    return
            return

        for pattern, call in self.pattern_to_function.items():
            if pattern.match(path):
                function, desc = call
                _logg.debug("Request %s matches (%s)", path, desc)
                return lambda req: call_and_close(function, req)

        # no pattern matched, use catchall handler if present
        if self.catchall_handler:
            return _partial(call_and_close, self.catchall_handler.f)

        return None


def _callhandler(handler_func, req):
    try:
        status = handler_func(req)
    except Exception as e:
        # XXX: this shouldn't be in Athana, most of it is mediaTUM-specific...
        # TODO: add some kind of exception handler system for Athana
        from utils.log import make_xid_and_errormsg_hash
        from core import db

        # Roll back if the error was caused by a database problem.
        # DB requests in this error handler will fail until rollback is called, so let's do it here.
        db.session.rollback()

        xid, hashed_errormsg, hashed_tb = make_xid_and_errormsg_hash()

        mail_to_address = _config.get('email.support')
        if not mail_to_address:
            _logg.warning("no support mail address configured, consider setting it with `email.support`")

        _logg.exception(u"exception (xid=%s) while handling request %s %s, %s",
                       xid, req.method, req.mediatum_contextfree_path, dict(req.args))

        if mail_to_address:
            msg = _core_translation.translate_in_request("core_snipped_internal_server_error_with_mail", req).replace(
                    '${email}',
                    mail_to_address,
                )
        else:
            msg = _core_translation.translate_in_request("core_snipped_internal_server_error_without_mail", req)
        s = msg.replace('${XID}', xid)
        req.response.headers["X-XID"] = xid
        req.response.status_code = _httpstatus.HTTP_INTERNAL_SERVER_ERROR
        req.response.set_data(s.encode("utf8"))


def handle_request(req):
    _flask.g.mediatum = {}

    maxlen = -1
    context = None
    global contexts
    for c in contexts:
        if req.path.startswith(c.name) and len(c.name) > maxlen:
            context = c
            maxlen = len(context.name)
    if context is None:
        req.response.status_code = _httpstatus.HTTP_NOT_FOUND
        return req

    mediatum_contextfree_path = req.path[len(context.name):]
    if not mediatum_contextfree_path.startswith("/"):
        mediatum_contextfree_path = "/" + mediatum_contextfree_path
    req.mediatum_contextfree_path = mediatum_contextfree_path

    req.params = {key: ";".join(value) for key, value in req.values.iterlists()}

    req.response = _flask.make_response()
    req.response.content_type = 'text/html; encoding=utf-8; charset=utf-8'

    try:
        for key in ("container_id", "id", "obj", "pid", "searchmaskitem_id", "show_id", "srcnodeid"):
            for value in req.values.getlist(key):
                for v in value.split(','):
                    int(v or 0)
    except ValueError:
        req.response.status_code = _httpstatus.HTTP_BAD_REQUEST
        req.response.set_data(_httpstatus.responses[req.response.status_code])
        return req

    function = context.match(mediatum_contextfree_path)
    if function is not None:
        _callhandler(function, req)
    else:
        _logg.debug("Request %s matches no pattern (context: %s)", req.path, context.name)
        req.response.set_data("File {} not found".format(req.path))
        req.response.status_code = _httpstatus.HTTP_NOT_FOUND

    return req


def addContext(webpath, localpath):
    global contexts
    c = _WebContext(webpath, localpath)
    contexts += [c]
    return c
