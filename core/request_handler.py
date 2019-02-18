import re as _re
import time as _time
import random as _random
import os as _os
import stat as _stat
import string as _string
import logging as _logging
import mimetypes as _mimetypes
import importlib as _importlib
import zipfile as _zipfile
import httpstatus as _httpstatus
import traceback as _traceback
import urllib as _urllib
import flask as _flask
import athana as _athana
import athana_z3950 as _athana_z3950
import utils.locks as _utils_lock
from functools import partial as _partial
from cgi import escape as _escape
from StringIO import StringIO as _StringIO
from core import config as _config
from werkzeug.datastructures import MIMEAccept as _MIMEAccept, ImmutableMultiDict as _ImmutableMultiDict
from werkzeug.http import parse_accept_header as _parse_accept_header
from utils.utils import suppress as _suppress, nullcontext as _nullcontext, counter as _counter
from utils.url import build_url_from_path_and_params as _build_url_from_path_and_params
from itertools import chain as _chain
from collections import OrderedDict as _OrderedDict
from wtforms.csrf.session import SessionCSRF as _SessionCSRF
from wtforms import Form as _Form
from wtforms.validators import ValidationError as _ValidationError
from datetime import timedelta as _timedelta
from utils.lrucache import lru_cache as _lru_cache


_logg = _logging.getLogger(__name__)

GLOBAL_TEMP_DIR = "/tmp/"
GLOBAL_ROOT_DIR = "no-root-dir-set"
CONNECTION = _re.compile('Connection: (.*)', _re.IGNORECASE)
# HTTP/1.0 doesn't say anything about the "; length=nnnn" addition
# to this header.  I suppose its purpose is to avoid the overhead
# of parsing dates...
IF_MODIFIED_SINCE = _re.compile(
    'If-Modified-Since: ([^;]+)((; length=([0-9]+)$)|$)',
    _re.IGNORECASE
)

# COMPAT: before / after request handlers and request / app context handling
_request_started_handlers = []
_request_finished_handlers = []

contexts = []
global_modules = {}

BASENAME = _re.compile("([^/]*/)*([^/.]*)(.py)?")
verbose = 1

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

mode_table = {
    '0': '---',
    '1': '--x',
    '2': '-w-',
    '3': '-wx',
    '4': 'r--',
    '5': 'r-x',
    '6': 'rw-',
    '7': 'rwx'
}


# http_date
def concat(*args):
    return ''.join(args)


def join(seq, field=' '):
    return field.join(seq)


def group(s):
    return '(' + s + ')'

short_days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
long_days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

short_day_reg = group(join(short_days, '|'))
long_day_reg = group(join(long_days, '|'))

daymap = {}
for i in range(7):
    daymap[short_days[i]] = i
    daymap[long_days[i]] = i

hms_reg = join(3 * [group('[0-9][0-9]')], ':')

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

monmap = {}
for i in range(12):
    monmap[months[i]] = i + 1

months_reg = group(join(months, '|'))

# From draft-ietf-http-v11-spec-07.txt/3.3.1
#       Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
#       Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
#       Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format

# rfc822 format
rfc822_date = join(
    [concat(short_day_reg, ','),    # day
     group('[0-9][0-9]?'),                  # date
     months_reg,                                    # month
     group('[0-9]+'),                               # year
     hms_reg,                                               # hour minute second
     'gmt'
     ],
    ' '
)

rfc822_reg = _re.compile(rfc822_date)


def unpack_rfc822(m):
    g = m.group
    a = _string.atoi
    return (
        a(g(4)),                # year
        monmap[g(3)],   # month
        a(g(2)),                # day
        a(g(5)),                # hour
        a(g(6)),                # minute
        a(g(7)),                # second
        0,
        0,
        0
    )

# rfc850 format
rfc850_date = join(
    [concat(long_day_reg, ','),
     join(
        [group('[0-9][0-9]?'),
         months_reg,
         group('[0-9]+')
         ],
        '-'
    ),
        hms_reg,
        'gmt'
    ],
    ' '
)

rfc850_reg = _re.compile(rfc850_date)
# they actually unpack the same way


def unpack_rfc850(m):
    g = m.group
    a = _string.atoi
    return (
        a(g(4)),                # year
        monmap[g(3)],   # month
        a(g(2)),                # day
        a(g(5)),                # hour
        a(g(6)),                # minute
        a(g(7)),                # second
        0,
        0,
        0
    )

# parsdate.parsedate    - ~700/sec.
# parse_http_date       - ~1333/sec.


def build_http_date(when):
    return _time.strftime('%a, %d %b %Y %H:%M:%S GMT', _time.gmtime(when))

time_offset = 0


def parse_http_date(d):
    global time_offset
    d = _string.lower(d)
    tz = _time.timezone
    m = rfc850_reg.match(d)
    if m and m.end() == len(d):
        retval = int(_time.mktime(unpack_rfc850(m)) - tz)
    else:
        m = rfc822_reg.match(d)
        if m and m.end() == len(d):
            try:
                retval = int(_time.mktime(unpack_rfc822(m)) - tz)
            except OverflowError:
                return 0
        else:
            return 0
    # Thanks to Craig Silverstein <csilvers@google.com> for pointing
    # out the DST discrepancy
    if _time.daylight and _time.localtime(retval)[-1] == 1:  # DST correction
        retval = retval + (tz - _time.altzone)
    return retval - time_offset


def check_date():
    global time_offset
    tmpfile = join_paths(GLOBAL_TEMP_DIR, "datetest" + ustr(_random.random()) + ".tmp")
    open(tmpfile, "wb").close()
    time1 = _os.stat(tmpfile)[_stat.ST_MTIME]
    _os.unlink(tmpfile)
    time2 = parse_http_date(build_http_date(_time.time()))
    time_offset = time2 - time1


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


# --------------------------------------------------
# split a uri according to https://tools.ietf.org/html/rfc3986
# --------------------------------------------------
def split_uri(req):
    # <path>;<params>?<query>#<fragment>
    path_regex = _re.compile(
        #      path      params    query   fragment
        r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?'
    )
    m = path_regex.match(req.uri)
    return m.groups()


def get_header(req, header):
    header = header.lower()
    if header not in req._header_cache:
        h = "{}:".format(header)
        for line in req.header:
            if line.lower().startswith(h):
                req._header_cache[header] = line[len(h):]
    return req._header_cache.get(header)


# standard wrapper around a unix-like filesystem, with a 'false root'
# capability.

# security considerations: can symbolic links be used to 'escape' the
# root?  should we allow it?  if not, then we could scan the
# filesystem on startup, but that would not help if they were added
# later.  We will probably need to check for symlinks in the cwd method.

# what to do if wd is an invalid directory?

def safe_stat(path):
    try:
        return (path, _os.stat(path))
    except:
        return None


# Emulate the unix 'ls' command's date field.
# it has two formats - if the date is more than 180
# days in the past, then it's like this:
# Oct 19  1995
# otherwise, it looks like this:
# Oct 19 17:33

def ls_date(now, t):
    try:
        info = _time.gmtime(t)
    except:
        info = _time.gmtime(0)
    # 15,600,000 == 86,400 * 180
    if (now - t) > 15600000:
        return '%s %2d  %d' % (
            months[info[1] - 1],
            info[2],
            info[0]
        )
    else:
        return '%s %2d %02d:%02d' % (
            months[info[1] - 1],
            info[2],
            info[3],
            info[4]
        )


def unix_longify(file, stat_info):
    # for now, only pay attention to the lower bits
    mode = ('%o' % stat_info[_stat.ST_MODE])[-3:]
    mode = _string.join(map(lambda x: mode_table[x], mode), '')
    if _stat.S_ISDIR(stat_info[_stat.ST_MODE]):
        dirchar = 'd'
    else:
        dirchar = '-'
    date = ls_date(long(_time.time()), stat_info[_stat.ST_MTIME])
    return '%s%s %3d %-8d %-8d %8d %s %s' % (
        dirchar,
        mode,
        stat_info[_stat.ST_NLINK],
        stat_info[_stat.ST_UID],
        stat_info[_stat.ST_GID],
        stat_info[_stat.ST_SIZE],
        date,
        file
    )


class FileStore:

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
        request.path = _escape(request.path)
        return error(request, 404, "File " + request.path + " not found")

    def addRoot(self, dir):
        if not _os.path.isabs(dir):
            dir = qualify_path(dir)
            while dir.startswith("./"):
                dir = dir[2:]
            dir = _os.path.join(GLOBAL_ROOT_DIR, dir)
        if _zipfile.is_zipfile(dir[:-1]) and dir.lower().endswith("zip/"):
            self.handlers += [default_handler(zip_filesystem(dir[:-1]))]
        else:
            self.handlers += [default_handler(os_filesystem(dir))]


class WebFile:

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
        handler = WebHandler(self, function)
        self.handlers += [handler]
        return handler

    def addCatchallHandler(self, function):
        handler = WebHandler(self, function)
        self.context.catchall_handler = handler
        return handler

    def addFTPHandler(self, ftpclass):
        global ftphandlers
        m = self.m
        with _nullcontext():
            c = eval("m." + ftpclass)
            if c is None:
                raise Exception("")
            ftphandlers += [c]

    def getFileName(self):
        return self.context.root + self.filename


class WebHandler:

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
        p = WebPattern(self, pattern)
        desc = "pattern %s, file %s, function %s" % (pattern, self.file.filename, self.function)
        self.file.context.pattern_to_function[p.getPattern()] = (self.f, desc)
        return p


class WebPattern:

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


class zip_filesystem:

    def __init__(self, filename):
        self.filename = filename
        self.wd = '/'
        self.m = {}
        self.z = _zipfile.ZipFile(filename)
        for f in self.z.filelist:
            self.m['/' + f.filename] = f

        if "/index.html" in self.m:
            self.m['/'] = self.m['/index.html']

    def current_directory(self):
        return self.wd

    def isfile(self, path):
        if len(path) and path[-1] == '/':
            return 0
        return (self.wd + path) in self.m

    def isdir(self, path):
        if not (len(path) and path[-1] == '/'):
            path += '/'
        return path in self.m

    def cwd(self, path):
        path = join_paths(self.wd, path)
        if not self.isdir(path):
            return 0
        else:
            self.wd = path
            return 1

    def cdup(self):
        try:
            i = self.wd[:-1].rindex('/')
            self.wd = self.wd[0:i + 1]
        except ValueError:
            self.wd = '/'
        return 1

    def listdir(self, path, long=0):
        raise NotImplementedError()

    # TODO: implement a cache w/timeout for stat()
    def stat(self, path):
        fullpath = join_paths(self.wd, path)
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

    def unlink(self, path):
        raise NotImplementedError()

    def mkdir(self, path):
        raise NotImplementedError()

    def rmdir(self, path):
        raise NotImplementedError()

    def longify(self, (path, stat_info)):
        return unix_longify(path, stat_info)

    def __repr__(self):
        return '<zipfile fs root:%s wd:%s>' % (self.filename, self.wd)


class os_filesystem:
    path_module = _os.path

    # set this to zero if you want to disable pathname globbing.
    # [we currently don't glob, anyway]
    do_globbing = 1

    def __init__(self, root, wd='/'):
        self.root = root
        self.wd = wd

    def current_directory(self):
        return self.wd

    def isfile(self, path):
        p = self.normalize(self.path_module.join(self.wd, path))
        return self.path_module.isfile(self.translate(p))

    def isdir(self, path):
        p = self.normalize(self.path_module.join(self.wd, path))
        return self.path_module.isdir(self.translate(p))

    def cwd(self, path):
        p = self.normalize(self.path_module.join(self.wd, path))
        translated_path = self.translate(p)
        if not self.path_module.isdir(translated_path):
            return 0
        else:
            old_dir = _os.getcwd()
            # temporarily change to that directory, in order
            # to see if we have permission to do so.
            try:
                can = 0
                with _suppress(Exception, warn=False):
                    _os.chdir(translated_path)
                    can = 1
                    self.wd = p
            finally:
                if can:
                    _os.chdir(old_dir)
            return can

    def cdup(self):
        return self.cwd('..')

    # TODO: implement a cache w/timeout for stat()
    def stat(self, path):
        p = self.translate(path)
        return _os.stat(p)

    def open(self, path, mode):
        p = self.translate(path)
        return open(p, mode)

    def unlink(self, path):
        p = self.translate(path)
        return _os.unlink(p)

    def mkdir(self, path):
        p = self.translate(path)
        return _os.mkdir(p)

    def rmdir(self, path):
        p = self.translate(path)
        return _os.rmdir(p)

    # utility methods
    def normalize(self, path):
        # watch for the ever-sneaky '/+' path element
        path = _re.sub('/+', '/', path)
        p = self.path_module.normpath(path)
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
        p = self.normalize(self.path_module.join(self.wd, path))
        p = self.normalize(self.path_module.join(self.root, p[1:]))
        return p

    def longify(self, (path, stat_info)):
        return unix_longify(path, stat_info)

    def __repr__(self):
        return '<unix-style fs root:%s wd:%s>' % (
            self.root,
            self.wd
        )


class MediatumForm(_Form):
    class Meta:
        csrf = True
        csrf_class = _SessionCSRF
        csrf_secret = str(_config.get('csrf.secret_key'))
        csrf_time_limit = _timedelta(int(_config.get('csrf.timeout', "7200")))

    def validate_csrf_token(self, field):
        try:
            self._csrf.validate_csrf_token(self._csrf, field)
        except _ValidationError as e:
            if (e.message == "CSRF token expired"):
                self.csrf_token.current_token = self._csrf.generate_csrf_token(field)
                csrf_errors = self.errors['csrf_token']
                csrf_errors.remove("CSRF token expired")
                if not any(csrf_errors):
                    self.errors.pop("csrf_token")


def done(req):
    "finalize this transaction - send output to the http channel"
    unlink_tempfiles(req)

    # ----------------------------------------
    # persistent connection management
    # ----------------------------------------

    #  --- BUCKLE UP! ----

    connection = _string.lower(get_header_from_match(CONNECTION, req.header))

    close_it = 0
    wrap_in_chunking = 0

    if req.version == '1.0':
        if connection == 'keep-alive':
            if not req.has_key('Content-Length'):
                close_it = 1
            else:
                req['Connection'] = 'Keep-Alive'
        else:
            close_it = 1
    elif req.version == '1.1':
        if connection == 'close':
            close_it = 1
        elif not req.has_key('Content-Length'):
            if req.has_key('Transfer-Encoding'):
                if not req['Transfer-Encoding'] == 'chunked':
                    close_it = 1
            elif req.use_chunked:
                req['Transfer-Encoding'] = 'chunked'
                wrap_in_chunking = 1
            else:
                close_it = 1
    elif req.version is None:
        # Although we don't *really* support http/0.9 (because we'd have to
        # use \r\n as a terminator, and it would just yuck up a lot of stuff)
        # it's very common for developers to not want to type a version number
        # when using telnet to debug a server.
        close_it = 1

    if "Cache-Control" not in req.reply_headers or not _config.getboolean("athana.allow_cache_header", False):
        req.reply_headers["Cache-Control"] = "no-cache"

    if req.reply_code == 500:
        # don't use Transfer-Encoding chunked because only an error message is displayed
        # this code is only necessary if a reply-header contains invalid characters but has
        # Transfer-Encoding chunked set
        req.use_chunked = 0
        if req.has_key('Transfer-Encoding'):
            if req['Transfer-Encoding'] == 'chunked':
                req['Transfer-Encoding'] = ''

    reply_header = req.build_reply_header(check_characters=req.reply_code != 500)
    if not reply_header:
        raise ValueError("invalid header field")

    outgoing_header = _athana_z3950.simple_producer(reply_header)

    if close_it:
        req['Connection'] = 'close'

    if wrap_in_chunking:
        outgoing_producer = _athana.chunked_producer(
            _athana.composite_producer(list(req.outgoing))
        )
        # prepend the header
        outgoing_producer = _athana.composite_producer(
            [outgoing_header, outgoing_producer]
        )
    else:
        # prepend the header
        req.outgoing.insert(0, outgoing_header)
        outgoing_producer = _athana.composite_producer(list(req.outgoing))

    # actually, this is already set to None by the handler:
    req.channel.current_request = None

    # apply a few final transformations to the output
    req.channel.push_with_producer(
        # globbing gives us large packets
        _athana.globbing_producer(
            outgoing_producer
        )
    )

    if close_it:
        req.channel.close_when_done()


def error(req, code, s=None, content_type='text/html'):
    req.reply_code = code
    req.outgoing = []
    message = _httpstatus.responses[code]
    if s is None:
        s = _httpstatus.DEFAULT_ERROR_MESSAGE % {
            'code': code,
            'message': message,
        }
    req['Content-Length'] = len(s)
    req['Content-Type'] = content_type
    # make an error reply
    req.push(s)
    done(req)


@_lru_cache(maxsize=128)
def accept_mimetypes(req):
    accept = _parse_accept_header(get_header(req, "ACCEPT"), _MIMEAccept)
    return accept


def unlink_tempfiles(req):
    unlinked_tempfiles = []
    if hasattr(req, "tempfiles"):
        for f in req.tempfiles:
            _os.unlink(f)
            unlinked_tempfiles.append(f)
            _logg.debug("unlinked tempfile %s", f)
    return unlinked_tempfiles


def get_header_from_match(head_reg, lines, group=1):
    for line in lines:
        m = head_reg.match(line)
        if m and m.end() == len(line):
            return m.group(group)
    return ''


def get_header_match(head_reg, lines):
    for line in lines:
        m = head_reg.match(line)
        if m and m.end() == len(line):
            return m
    return ''


def sendFile(req, path, content_type, force=0, nginx_x_accel_redirect_enabled=True):
    if isinstance(path, unicode):
        path = path.encode("utf8")

    if isinstance(content_type, unicode):
        content_type = content_type.encode("utf8")

    x_accel_redirect = _config.get("nginx.X-Accel-Redirect", "").lower() == "true" and nginx_x_accel_redirect_enabled
    file = None
    file_length = 0

    if not x_accel_redirect:
        try:
            file_length = _os.stat(path)[_stat.ST_SIZE]
        except OSError:
            error(req, 404)
            return

    ims = get_header_match(IF_MODIFIED_SINCE, req.header)
    length_match = 1
    if ims:
        length = ims.group(4)
        if length:
            with _suppress(Exception, warn=False):
                length = _string.atoi(length)
                if length != file_length:
                    length_match = 0

    ims_date = 0
    if ims:
        ims_date = parse_http_date(ims.group(1))

    try:
        mtime = _os.stat(path)[_stat.ST_MTIME]
    except:
        error(req, 404)
        return
    if length_match and ims_date:
        if mtime <= ims_date and not force:
            # print "File "+path+" was not modified since "+ustr(ims_date)+" (current filedate is "+ustr(mtime)+")-> 304"
            req.reply_code = 304
            return

    if not x_accel_redirect:
        try:
            file = open(path, 'rb')
        except IOError:
            error(req, 404)
            print "404"
            return

    req.reply_headers['Last-Modified'] = build_http_date(mtime)
    req.reply_headers['Content-Length'] = file_length
    req.reply_headers['Content-Type'] = content_type
    if x_accel_redirect:
        req.reply_headers['X-Accel-Redirect'] = path
    if req.command == 'GET':
        if x_accel_redirect:
            done(req)
        else:
            req.push(_athana.file_producer(file))
    return


def get_extension(path):
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


def sendAsBuffer(req, text, content_type, force=0, allow_cross_origin=False):
    stringio = _StringIO(text)
    try:
        file_length = len(stringio.buf)
    except OSError:
        error(req, 404)
        return

    ims = get_header_match(IF_MODIFIED_SINCE, req.header)
    length_match = 1
    if ims:
        length = ims.group(4)
        if length:
            with _suppress(Exception, warn=False):
                length = _string.atoi(length)
                if length != file_length:
                    length_match = 0

    ims_date = 0
    if ims:
        ims_date = parse_http_date(ims.group(1))

    try:
        import time
        mtime = _time.time()  # _os.stat (path)[stat.ST_MTIME]
    except:
        error(req, 404)
        return

    if length_match and ims_date:
        if mtime <= ims_date and not force:
            req.reply_code = 304
            return
    try:
        file = stringio
    except IOError:
        error(req, 404)
        return

    req.reply_headers['Last-Modified'] = build_http_date(mtime)
    req.reply_headers['Content-Length'] = file_length
    req.reply_headers['Content-Type'] = content_type
    if allow_cross_origin:
        req.reply_headers['Access-Control-Allow-Origin'] = '*'
    if req.command == 'GET':
        req.push(_athana.file_producer(file))
    return


def setCookie(req, name, value, expire=None, path=None, http_only=True, secure=False):
    parts = [name + '=' + value]

    if expire:
        datestr = _time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", _time.gmtime(expire))
        parts.append('expires=' + datestr)

    if path:
        parts.append("path=" + path)

    if http_only:
        parts.append("HttpOnly")

    if secure:
        parts.append("Secure")

    cookie_str = "; ".join(parts)

    if 'Set-Cookie' not in req.reply_headers:
        req.reply_headers['Set-Cookie'] = [cookie_str]
    else:
        req.reply_headers['Set-Cookie'] += [cookie_str]


def makeSelfLink(req, params):
    params2 = req.params.copy()
    for k, v in params.items():
        if v is not None:
            params2[k] = v
        else:
            with _suppress(Exception, warn=False):
                del params2[k]
    ret = _build_url_from_path_and_params(req.fullpath, params2)
    return ret


# COMPAT: new param style like flask
def make_legacy_params_dict(req):
    """convert new-style params to old style athana params dict"""
    req.params = params = {}
    for key, values in _chain(req.form.iterlists(), req.args.iterlists()):
        value = ";".join(values)
        params[key] = value
#             params[key.encode("utf8")] = value.encode("utf8")
    params.update(req.files.iteritems())


# COMPAT: added functions

def request_started(handler):
    """Decorator for functions which should be run before the view handler is called"""
    _request_started_handlers.append(handler)
    return handler


def request_finished(handler):
    """Decorator for functions which should be run after the view handler is called"""
    _request_finished_handlers.append(handler)
    return handler


def make_param_dict_utf8_values(param_list):
    def decode(k):
        try:
            return unicode(k, encoding="utf8")
        except UnicodeDecodeError as e:
            _logg.warn("tried to decode non-UTF8 string: %s", k.encode("string-escape"))
            raise

    return _ImmutableMultiDict([(decode(k), decode(v)) for k, v in param_list])


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

class default_handler:
    valid_commands = ['GET', 'HEAD']

    IDENT = 'Default HTTP Request Handler'

    # Pathnames that are tried when a URI resolves to a directory name
    directory_defaults = [
        'index.html',
        'default.html'
    ]

    def __init__(self, filesystem):
        self.filesystem = filesystem
        # count total hits
        self.hit_counter = _counter()
        # count file deliveries
        self.file_counter = _counter()
        # count cache hits
        self.cache_counter = _counter()
        self.default_file_producer = _athana.file_producer

    hit_counter = 0

    def __repr__(self):
        return '<%s (%s hits) at %x>' % (
            self.IDENT,
            self.hit_counter,
            id(self)
        )

    # always match, since this is a default
    def match(self, request):
        return 1

    def can_handle(self, request):
        path, params, query, fragment = split_uri(request)
        if '%' in path:
            path = _urllib.unquote(path)
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

        if request.command not in self.valid_commands:
            error(request, 400)  # bad request
            return

        self.hit_counter.increment()
        path, params, query, fragment = split_uri(request)

        if '%' in path:
            path = _urllib.unquote(path)

        # strip off all leading slashes
        while path and path[0] == '/':
            path = path[1:]

        if self.filesystem.isdir(path):
            if path and path[-1] != '/':
                request['Location'] = 'http://%s/%s/' % (
                    request.channel.server.server_name,
                    path
                )
                error(request, 301)
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
                error(request, 404)  # Not Found
                return

        elif not self.filesystem.isfile(path):
            error(request, 404)  # Not Found
            return

        file_length = self.filesystem.stat(path)[_stat.ST_SIZE]

        ims = get_header_match(IF_MODIFIED_SINCE, request.header)

        length_match = 1
        if ims:
            length = ims.group(4)
            if length:
                with _suppress(Exception, warn=False):
                    length = _string.atoi(length)
                    if length != file_length:
                        length_match = 0
        ims_date = 0

        if ims:
            ims_date = parse_http_date(ims.group(1))

        try:
            mtime = self.filesystem.stat(path)[_stat.ST_MTIME]
        except:
            error(request, 404)
            return

        if length_match and ims_date:
            if mtime <= ims_date:
                request.reply_code = 304
                done(request)
                self.cache_counter.increment()
                # print "File "+path+" was not modified since "+ustr(ims_date)+" (current filedate is "+ustr(mtime)+")"
                return
        try:
            file = self.filesystem.open(path, 'rb')
        except IOError:
            error(request, 404)
            return

        request['Last-Modified'] = build_http_date(mtime)
        request['Content-Length'] = file_length
        self.set_content_type(path, request)

        if request.command == 'GET':
            request.push(self.default_file_producer(file))

        self.file_counter.increment()
        done(request)

    def set_content_type(self, path, request):
        ext = _string.lower(get_extension(path))
        typ, encoding = _mimetypes.guess_type(path)
        if typ is not None:
            request['Content-Type'] = typ
        else:
            # TODO: test a chunk off the front of the file for 8-bit
            # characters, and use application/octet-stream instead.
            request['Content-Type'] = 'text/plain'

    def status(self):
        return _athana_z3950.simple_producer(
            '<li>%s' % html_repr(self)
            + '<ul>'
            + '  <li><b>Total Hits:</b> %s' % self.hit_counter
            + '  <li><b>Files Delivered:</b> %s' % self.file_counter
            + '  <li><b>Cache Hits:</b> %s' % self.cache_counter
            + '</ul>'
        )


class WebContext:

    def __init__(self, name, root=None):
        self.name = name
        self.files = []
        self.startupfile = None
        if root:
            self.root = qualify_path(root)
        self.pattern_to_function = _OrderedDict()
        self.catchall_handler = None

    def addFile(self, filename, module=None):
        file = WebFile(self, filename, module)
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
                req.reply_code = status
                if(status >= 400 and status <= 500):
                    return error(req, status)
            return done(req)

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


def callhandler(handler_func, req):
    for handler in _request_started_handlers:
        handler(req)

    try:
        status = handler_func(req)
    except Exception as e:
        # XXX: this shouldn't be in Athana, most of it is mediaTUM-specific...
        # TODO: add some kind of exception handler system for Athana
        request = req.request
        if _config.get('host.type') != 'testing':
            from utils.log import make_xid_and_errormsg_hash, extra_log_info_from_req
            from core.translation import translate
            from core import db

            # Roll back if the error was caused by a database problem.
            # DB requests in this error handler will fail until rollback is called, so let's do it here.
            db.session.rollback()

            xid, hashed_errormsg, hashed_tb = make_xid_and_errormsg_hash()

            mail_to_address = _config.get('email.support')
            if not mail_to_address:
                _logg.warn("no support mail address configured, consider setting it with `email.support`",
                          trace=False)

            log_extra = {"xid": xid,
                         "error_hash": hashed_errormsg,
                         "trace_hash": hashed_tb}

            log_extra["req"] = extra_log_info_from_req(req)

            _logg.exception(u"exception (xid=%s) while handling request %s %s, %s",
                           xid, req.method, req.path, dict(req.args), extra=log_extra)

            if mail_to_address:
                msg = translate("core_snipped_internal_server_error_with_mail", request=req).replace('${email}',
                                                                                                     mail_to_address)
            else:
                msg = translate("core_snipped_internal_server_error_without_mail", request=req)
            s = msg.replace('${XID}', xid)

            req.reply_headers["X-XID"] = xid
            return error(request, 500, s.encode("utf8"), content_type='text/html; encoding=utf-8; charset=utf-8')

        else:
            _logg.error("Error in page: '%s %s'", request.type, request.fullpath, exc_info=1)
            s = "<pre>" + _traceback.format_exc() + "</pre>"
            return error(request, 500, s)

    finally:
        for handler in _request_finished_handlers:
            handler(req)


def handle_request(handler, request, form):

    path, params, query, fragment = split_uri(request)

    ip = request.request_headers.get("x-forwarded-for", None)
    if ip is None:
        with _suppress(Exception, warn=False):
            ip = request.channel.addr[0]
    if ip:
        request.channel.addr = (ip, request.channel.addr[1])

    request.log()

    # COMPAT: new param style like flask
    if query is not None:
        args = _athana.AthanaHandler.parse_query(query)
    else:
        args = []
    # /COMPAT
    path = _urllib.unquote(path)
    if params is not None:
        params = _urllib.unquote(params)
    if fragment is not None:
        fragment = _urllib.unquote(fragment)

    cookies = {}
    if "cookie" in request.request_headers:
        cookiestr = request.request_headers["cookie"]
        if cookiestr.rfind(";") == len(cookiestr) - 1:
            cookiestr = cookiestr[:-1]
        items = cookiestr.split(';')
        for a in items:
            a = a.strip()
            i = a.find('=')
            if i > 0:
                key, value = a[:i], a[i + 1:]
                cookies[key] = value
            else:
                _logg.warn("corrupt cookie value: %s", a.encode("string-escape"))

    request.Cookies = cookies
    request['Content-Type'] = 'text/html; encoding=utf-8; charset=utf-8'

    maxlen = -1
    context = None
    global contexts
    for c in contexts:
        if path.startswith(c.name) and len(c.name) > maxlen:
            context = c
            maxlen = len(context.name)

    if context is None:
        error(request, 404)
        return

    fullpath = path
    path = path[len(context.name):]
    if len(path) == 0 or path[0] != '/':
        path = "/" + path

    request.context = context
    request.path = path
    request.fullpath = fullpath
    request.paramstring = params
    request.query = query
    request.fragment = fragment

    # COMPAT: new param style like flask
    # we don't need this for WSGI, args / form parsing is done by the WSGI app
    if not isinstance(context, _athana.WSGIContext):
        form, files = _athana.filter_out_files(form)
        try:
            request.args = make_param_dict_utf8_values(args)
            if "csrf_token" in request.args:
                form.append(('csrf_token', str(request.args["csrf_token"])))
            request.form = make_param_dict_utf8_values(form)
        except UnicodeDecodeError:
            return error(request, 400)

        mediatum_form = MediatumForm(meta={'csrf_context': _flask.session})
        if form and request.method == 'POST':
            if 'csrf_token' not in request.form:
                raise ValueError("csrf_token not in form of request path " + request.fullpath)
            else:
                mediatum_form.csrf_token.process_data(request.form["csrf_token"].replace("!!!!!", "##"))
                mediatum_form.validate()

        request.csrf_token = mediatum_form.csrf_token
        request.files = _ImmutableMultiDict(files)
        make_legacy_params_dict(request)

    # /COMPAT
    request.request = request
    request.ip = ip
    request.uri = request.uri.replace(context.name, "/")
    request._split_uri = None

    request.channel.current_request = None

    if path == "/threadstatus":
        return _athana.thread_status(request)
    if path == "/profilingstatus":
        return _athana.profiling_status(request)

    function = context.match(path)

    if function is None:
        _logg.debug("Request %s matches no pattern (context: %s)", request.path, context.name)
        request.path = _escape(request.path)
        return error(request, 404, "File %s not found" % request.path)
    if _athana.multithreading_enabled:
        handler.queuelock.acquire()
        handler.queue += [(function, request)]
        handler.queuelock.release()
    else:
        _athana.call_handler_func(function, request)


def addFileStore(webpath, localpaths):
    global contexts
    if len(webpath) and webpath[0] != '/':
        webpath = "/" + webpath
    c = FileStore(webpath, localpaths)
    contexts += [c]
    return c


def addFileStorePath(webpath, path):
    for context in contexts:
        if context.name == webpath:
            if path not in context.handlers:
                context.addRoot(path)


def addContext(webpath, localpath):
    global contexts
    c = WebContext(webpath, localpath)
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
