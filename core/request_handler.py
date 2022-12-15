# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import datetime as _datetime
import re as _re
import os as _os
import stat as _stat
import string as _string
import traceback as _traceback
import logging as _logging
import mimetypes as _mimetypes
import importlib as _importlib
import zipfile as _zipfile

from cgi import escape as _escape
from functools import partial as _partial

import flask as _flask

import core.translation as _core_translation
import httpstatus as _httpstatus
import utils.locks as _utils_lock
import csrfform as _csrfform
from core import config as _config
from utils.utils import suppress as _suppress, nullcontext as _nullcontext
from utils.url import build_url_from_path_and_params as _build_url_from_path_and_params
from collections import OrderedDict as _OrderedDict

_logg = _logging.getLogger(__name__)

GLOBAL_TEMP_DIR = "/tmp/"
GLOBAL_ROOT_DIR = "no-root-dir-set"

# COMPAT: before / after request handlers and request / app context handling
_request_started_handlers = []
_request_finished_handlers = []

contexts = []
global_modules = {}

BASENAME = _re.compile("([^/]*/)*([^/.]*)(.py)?")
verbose = 1


def join_paths(p1, p2):
    if p1.endswith("/"):
        if p2.startswith("/"):
            return p1[:-1] + p2
        else:
            return p1 + p2
    else:
        if p2.startswith("/"):
            return p1 + p2
        else:
            return p1 + "/" + p2


def qualify_path(p):
    if p[-1] != '/':
        return p + "/"
    return p


def setBase(base):
    global GLOBAL_ROOT_DIR
    GLOBAL_ROOT_DIR = qualify_path(base)


def setTempDir(tempdir):
    global GLOBAL_TEMP_DIR
    GLOBAL_TEMP_DIR = qualify_path(tempdir)


def getBase():
    return GLOBAL_ROOT_DIR


class _FileStore:

    def __init__(self, name, root=None):
        self.name = name
        self.handlers = []
        if type(root) == type(""):
            self.addRoot(root)
        elif type(root) == type([]):
            for dir in root:
                self.addRoot(dir)

    def match(self, path):
        return lambda req: self.findfile(req)

    def findfile(self, request):
        for handler in self.handlers:
            if handler.can_handle(request):
                return handler.handle_request(request)
        request.mediatum_contextfree_path = _escape(request.mediatum_contextfree_path)
        return _error(request, 404, "File " + request.mediatum_contextfree_path + " not found")

    def addRoot(self, dir):
        if not _os.path.isabs(dir):
            dir = qualify_path(dir)
            while dir.startswith("./"):
                dir = dir[2:]
            dir = _os.path.join(GLOBAL_ROOT_DIR, dir)
        if _zipfile.is_zipfile(dir[:-1]) and dir.lower().endswith("zip/"):
            self.handlers.insert(0, _default_handler(_ZipFilesystem(dir[:-1])))
        else:
            self.handlers.insert(0, _default_handler(_OSFilesystem(dir)))


class _WebFile:

    def __init__(self, context, filename, module=None):
        self.context = context
        if filename[0] == '/':
            filename = filename[1:]
        self.filename = filename
        if module is None:
            self.m = _load_module(join_paths(context.root, filename))
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
            with _nullcontext():
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


class _ZipFilesystem:

    def __init__(self, filename):
        self.filename = filename
        self.m = {}
        self.z = _zipfile.ZipFile(filename)
        for f in self.z.filelist:
            self.m['/' + f.filename] = f

        if "/index.html" in self.m:
            self.m['/'] = self.m['/index.html']

    def isfile(self, path):
        if len(path) and path[-1] == '/':
            return 0
        return _os.path.join("/", path) in self.m

    def isdir(self, path):
        if not (len(path) and path[-1] == '/'):
            path += '/'
        return path in self.m

    # TODO: implement a cache w/timeout for stat()
    def stat(self, path):
        fullpath = join_paths("/", path)
        if self.isfile(path):
            size = self.m[fullpath].file_size
            return (33188, 77396L, 10L, 1, 1000, 1000, size, 0, 0, 0)
        elif self.isdir(path):
            return (16895, 117481L, 10L, 20, 1000, 1000, 4096L, 0, 0, 0)
        else:
            raise IOError("No such file or directory " + path)

    def open(self, path, mode):
        class zFile:

            def __init__(self, content):
                self.content = content
                self.pos = 0
                self.len = len(content)

            def read(self, l=None):
                if l is None:
                    l = self.len - self.pos
                if self.len < self.pos + l:
                    l = self.len - self.pos
                s = self.content[self.pos: self.pos + l]
                self.pos += l
                return s

            def close(self):
                del self.content
                del self.len
                del self.pos

        with _utils_lock.named_lock("zipfile"):
            data = self.z.read(path)

        return zFile(data)


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



def _error(req, code, s=None, content_type='text/html'):
    req.response.status_code = code
    message = _httpstatus.responses[code]
    if s is None:
        s = _httpstatus.DEFAULT_ERROR_MESSAGE % {
            'code': code,
            'message': message,
        }
    req.response.content_length = len(s)
    req.response.content_type = content_type
    req.response.set_data(s)


def sendFile(req, path, content_type, force=0, nginx_x_accel_redirect_enabled=True):
    if isinstance(path, unicode):
        path = path.encode("utf8")

    if isinstance(content_type, unicode):
        content_type = content_type.encode("utf8")

    _logg.debug("sendFile: %s", path)

    assert _os.path.isabs(path), "sendFile: path: {} is not an absolute path".format(path)

    if nginx_x_accel_redirect_enabled:
        # TODO: It should be checked if a path is a subdirectory of another path.
        #       This would be a configuration error by the admin.
        for nginx_alias, nginx_dir in _config.getsubset("nginx-redirect").iteritems():
            assert _os.path.isabs(nginx_dir), "sendFile: nginx_dir: {} is not an absolute path".format(nginx_dir)
            if not _os.path.relpath(path, nginx_dir).startswith("../"):
                break
        else:
            nginx_alias = None
    else:
        nginx_alias = None

    file_length = 0

    if not nginx_alias:
        try:
            file_length = _os.stat(path)[_stat.ST_SIZE]
        except OSError:
            _error(req, 404)
            return

    try:
        mtime = _datetime.datetime.utcfromtimestamp(_os.stat(path)[_stat.ST_MTIME])
    except:
        _error(req, 404)
        return
    if req.if_modified_since:
        if mtime <= req.if_modified_since and not force:
            req.response.status_code = 304
            return

    req.response.last_modified = mtime
    req.response.content_length = file_length
    req.response.content_type = content_type
    if nginx_alias:
        req.response.headers['X-Accel-Redirect'] = _os.path.join("/{}".format(nginx_alias), _os.path.relpath(path, nginx_dir))
    if req.method == 'GET':
        if nginx_alias:
            return
        else:
            req.response = _flask.send_file(path, conditional=True)
            req.response.content_length = file_length
    req.response.status_code = _httpstatus.HTTP_OK
    return


def _get_extension(path):
    dirsep = _string.rfind(path, '/')
    dotsep = _string.rfind(path, '.')
    if dotsep > dirsep:
        return path[dotsep + 1:]
    else:
        return ''


def html_repr(object):
    so = _escape(repr(object))
    if hasattr(object, 'hyper_respond'):
        return '<a href="/status/object/%d/">%s</a>' % (id(object), so)
    else:
        return so


def makeSelfLink(req, params):
    params2 = req.params.copy()
    for k, v in params.items():
        if v is not None:
            params2[k] = v
        else:
            with _suppress(Exception, warn=False):
                del params2[k]
    ret = _build_url_from_path_and_params(req.path, params2)
    return ret


# COMPAT: added functions

def request_started(handler):
    """Decorator for functions which should be run before the view handler is called"""
    _request_started_handlers.append(handler)
    return handler


def request_finished(handler):
    """Decorator for functions which should be run after the view handler is called"""
    _request_finished_handlers.append(handler)
    return handler


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


# This is the 'default' handler.  it implements the base set of
# features expected of a simple file-delivering HTTP server.  file
# services are provided through a 'filesystem' object, the very same
# one used by the FTP server.
#
# You can replace or modify this handler if you want a non-standard
# HTTP server.  You can also derive your own handler classes from
# it.
#
# support for handling POST requests is available in the derived
# class <default_with_post_handler>, defined below.
#

class _default_handler:
    valid_commands = ['GET', 'HEAD']

    IDENT = 'Default HTTP Request Handler'

    # Pathnames that are tried when a URI resolves to a directory name
    directory_defaults = [
        'index.html',
        'default.html'
    ]

    def __init__(self, filesystem):
        self.filesystem = filesystem

    # always match, since this is a default
    def match(self, request):
        return 1

    def can_handle(self, request):
        path = request.mediatum_contextfree_path
        while path and path[0] == '/':
            path = path[1:]
        if self.filesystem.isdir(path):
            if path and path[-1] != '/':
                return 0
            found = 0
            if path and path[-1] != '/':
                path = path + '/'
            for default in self.directory_defaults:
                p = path + default
                if self.filesystem.isfile(p):
                    path = p
                    found = 1
                    break
            if not found:
                return 0
        elif not self.filesystem.isfile(path):
            return 0
        return 1

    # handle a file request, with caching.

    def handle_request(self, request):

        if request.method not in self.valid_commands:
            _error(request, 400)  # bad request
            return

        path = request.mediatum_contextfree_path

        # strip off all leading slashes
        while path and path[0] == '/':
            path = path[1:]

        if self.filesystem.isdir(path):
            if path and path[-1] != '/':
                request.response.location = '%s%s/' % (request.host_url, path)
                _error(request, 301)
                return

            # we could also generate a directory listing here,
            # may want to move this into another method for that
            # purpose
            found = 0
            if path and path[-1] != '/':
                path = path + '/'
            for default in self.directory_defaults:
                p = path + default
                if self.filesystem.isfile(p):
                    path = p
                    found = 1
                    break
            if not found:
                _error(request, 404)  # Not Found
                return

        elif not self.filesystem.isfile(path):
            _error(request, 404)  # Not Found
            return

        file_length = self.filesystem.stat(path)[_stat.ST_SIZE]

        try:
            mtime = _datetime.datetime.utcfromtimestamp(self.filesystem.stat(path)[_stat.ST_MTIME])
        except:
            _error(request, 404)
            return

        if request.if_modified_since:
            if mtime <= request.if_modified_since:
                request.response.status_code = 304
                return
        try:
            file = self.filesystem.open(path, 'rb')
        except IOError:
            _error(request, 404)
            return

        request.response.last_modified = mtime
        request.response.content_length = file_length
        self.set_content_type(path, request)

        if request.method == 'GET':
            request.response.set_data(file.read())

    def set_content_type(self, path, request):
        ext = _string.lower(_get_extension(path))
        typ, encoding = _mimetypes.guess_type(path)
        if typ is not None:
            request.response.content_type = typ
        else:
            # TODO: test a chunk off the front of the file for 8-bit
            # characters, and use application/octet-stream instead.
            request.response.content_type = 'text/plain'


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

    def setRoot(self, root):
        self.root = qualify_path(root)
        while self.root.startswith("./"):
            self.root = self.root[2:]

    def setStartupFile(self, startupfile):
        self.startupfile = startupfile
        _logg.info("  executing startupfile")
        self._load_module(self.startupfile)

    def getStartupFile(self):
        return self.startupfile

    def match(self, path):
        def call_and_close(f, req):
            status = f(req)
            if type("1") == type(status):
                status = int(status)
            if status is not None and type(1) == type(status) and status > 10:
                req.response.status_code = status
                if(status >= 400 and status <= 500):
                    return _error(req, status)
            return

        for pattern, call in self.pattern_to_function.items():
            if pattern.match(path):
                function, desc = call
                if verbose:
                    _logg.debug("Request %s matches (%s)", path, desc)
                return lambda req: call_and_close(function, req)

        # no pattern matched, use catchall handler if present
        if self.catchall_handler:
            return _partial(call_and_close, self.catchall_handler.f)

        return None


def _callhandler(handler_func, req):
    for handler in _request_started_handlers:
        handler(req)

    try:
        status = handler_func(req)
    except Exception as e:
        # XXX: this shouldn't be in Athana, most of it is mediaTUM-specific...
        # TODO: add some kind of exception handler system for Athana
        if _config.get('host.type') != 'testing':
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
                msg = _core_translation.translate_in_request(
                        "core_snipped_internal_server_error_with_mail",
                        req,
                    ).replace('${email}', mail_to_address)
            else:
                msg = _core_translation.translate_in_request("core_snipped_internal_server_error_without_mail", req)
            s = msg.replace('${XID}', xid)

            req.response.headers["X-XID"] = xid
            return _error(req, 500, s.encode("utf8"), content_type='text/html; encoding=utf-8; charset=utf-8')

        else:
            _logg.exception("Error in page: '%s %s'", req.method, req.full_path)
            s = "<pre>" + _traceback.format_exc() + "</pre>"
            return _error(req, 500, s)

    finally:
        for handler in _request_finished_handlers:
            handler(req)


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
        _error(req, 404)
        return req

    mediatum_contextfree_path = req.path[len(context.name):]
    if not mediatum_contextfree_path.startswith("/"):
        mediatum_contextfree_path = "/" + mediatum_contextfree_path
    req.mediatum_contextfree_path = mediatum_contextfree_path

    req.params = {key: ";".join(value) for key, value in req.values.iterlists()}

    req.response = _flask.make_response()
    req.response.content_type = 'text/html; encoding=utf-8; charset=utf-8'

    function = context.match(mediatum_contextfree_path)
    if function is not None:
        _callhandler(function, req)
    else:
        _logg.debug("Request %s matches no pattern (context: %s)", req.path, context.name)
        _error(req, 404, "File %s not found" % req.path)

    return req


def addFileStore(webpath, localpaths):
    global contexts
    if len(webpath) and webpath[0] != '/':
        webpath = "/" + webpath
    c = _FileStore(webpath, localpaths)
    contexts += [c]
    return c


def addFileStorePath(webpath, path):
    for context in contexts:
        if context.name == webpath:
            if path not in context.handlers:
                context.addRoot(path)


def addContext(webpath, localpath):
    global contexts
    c = _WebContext(webpath, localpath)
    contexts += [c]
    return c


def getFileStorePaths(webpath):
    global contexts
    ret = []
    for context in contexts:
        if context.name == webpath:
            for h in context.handlers:
                ret.append(h.filesystem.root)
    return ret
