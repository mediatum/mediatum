#!/usr/bin/python
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
from werkzeug._compat import wsgi_encoding_dance
from werkzeug.http import parse_accept_header
from werkzeug.utils import cached_property
from array import array

#===============================================================
#
# Athana
#
# A standalone webserver based on Medusa and the Zope TAL Parser
#
# This file is distributed under the GPL, see file COPYING for details.
#
#===============================================================
RCS_ID = '$Id: athana.py,v 1.48 2013/02/28 07:28:19 seiferta Exp $'

import re
import string

from functools import partial
from itertools import chain
import logging
from werkzeug.datastructures import ImmutableMultiDict, MIMEAccept
from mediatumtal import tal


logg = logging.getLogger(__name__)
logftp = logging.getLogger(__name__ + ":ftp")


class AthanaException(Exception):
    pass

_ent1_re = re.compile('&(?![A-Z#])', re.I)
_entch_re = re.compile('&([A-Z][A-Z0-9]*)(?![A-Z0-9;])', re.I)
_entn1_re = re.compile('&#(?![0-9X])', re.I)
_entnx_re = re.compile('&(#X[A-F0-9]*)(?![A-F0-9;])', re.I)
_entnd_re = re.compile('&(#[0-9][0-9]*)(?![0-9;])')


def attrEscape(s):
    """Replace special characters '&<>' by character entities,
    except when '&' already begins a syntactically valid entity."""
    s = _ent1_re.sub('&amp;', s)
    s = _entch_re.sub(r'&amp;\1', s)
    s = _entn1_re.sub('&amp;#', s)
    s = _entnx_re.sub(r'&amp;\1', s)
    s = _entnd_re.sub(r'&amp;\1', s)
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    s = s.replace('"', '&quot;')
    return s

# ================ MEDUSA ===============

# python modules
import os
import select
import sys
import time
import stat
import mimetypes
from cgi import escape
from urllib import unquote, splitquery
from collections import OrderedDict
from core import config

# async modules
import asyncore
import socket



class async_chat (asyncore.dispatcher):

    """This is an abstract class.  You must derive from this class, and add
    the two methods collect_incoming_data() and found_terminator()"""

    # these are overridable defaults

    ac_in_buffer_size = 4096
    ac_out_buffer_size = 4096

    def __init__(self, conn=None):
        self.ac_in_buffer = ''
        self.ac_out_buffer = ''
        self.producer_fifo = fifo()
        asyncore.dispatcher.__init__(self, conn)

    def collect_incoming_data(self, data):
        raise NotImplementedError("must be implemented in subclass")

    def found_terminator(self):
        raise NotImplementedError("must be implemented in subclass")

    def set_terminator(self, term):
        "Set the input delimiter.  Can be a fixed string of any length, an integer, or None"
        self.terminator = term

    def get_terminator(self):
        return self.terminator

    # grab some more data from the socket,
    # throw it to the collector method,
    # check for the terminator,
    # if found, transition to the next state.

    def handle_read(self):

        try:
            data = self.recv(self.ac_in_buffer_size)
        except socket.error, why:
            self.handle_error()
            return

        self.ac_in_buffer = self.ac_in_buffer + data

        # Continue to search for self.terminator in self.ac_in_buffer,
        # while calling self.collect_incoming_data.  The while loop
        # is necessary because we might read several data+terminator
        # combos with a single recv(1024).

        while self.ac_in_buffer:
            lb = len(self.ac_in_buffer)
            terminator = self.get_terminator()
            if terminator is None or terminator == '':
                # no terminator, collect it all
                self.collect_incoming_data(self.ac_in_buffer)
                self.ac_in_buffer = ''
            elif isinstance(terminator, int):
                # numeric terminator
                n = terminator
                if lb < n:
                    self.collect_incoming_data(self.ac_in_buffer)
                    self.ac_in_buffer = ''
                    self.terminator = self.terminator - lb
                else:
                    self.collect_incoming_data(self.ac_in_buffer[:n])
                    self.ac_in_buffer = self.ac_in_buffer[n:]
                    self.terminator = 0
                    self.found_terminator()
            else:
                # 3 cases:
                # 1) end of buffer matches terminator exactly:
                #    collect data, transition
                # 2) end of buffer matches some prefix:
                #    collect data to the prefix
                # 3) end of buffer does not match any prefix:
                #    collect data
                terminator_len = len(terminator)
                index = self.ac_in_buffer.find(terminator)
                if index != -1:
                    # we found the terminator
                    if index > 0:
                        # don't bother reporting the empty string (source of subtle bugs)
                        self.collect_incoming_data(self.ac_in_buffer[:index])
                    self.ac_in_buffer = self.ac_in_buffer[index + terminator_len:]
                    # This does the Right Thing if the terminator is changed here.
                    self.found_terminator()
                else:
                    # check for a prefix of the terminator
                    index = find_prefix_at_end(self.ac_in_buffer, terminator)
                    if index:
                        if index != lb:
                            # we found a prefix, collect up to the prefix
                            self.collect_incoming_data(self.ac_in_buffer[:-index])
                            self.ac_in_buffer = self.ac_in_buffer[-index:]
                        break
                    else:
                        # no prefix, collect it all
                        self.collect_incoming_data(self.ac_in_buffer)
                        self.ac_in_buffer = ''

    def handle_write(self):
        self.initiate_send()

    def handle_close(self):
        self.close()

    def push(self, data):
        self.producer_fifo.push(simple_producer(data))
        self.initiate_send()

    def push_with_producer(self, producer):
        self.producer_fifo.push(producer)
        self.initiate_send()

    def readable(self):
        "predicate for inclusion in the readable for select()"
        return (len(self.ac_in_buffer) <= self.ac_in_buffer_size)

    def writable(self):
        "predicate for inclusion in the writable for select()"
        # return len(self.ac_out_buffer) or len(self.producer_fifo) or (not self.connected)
        # this is about twice as fast, though not as clear.
        return not (
            (self.ac_out_buffer == '') and
            self.producer_fifo.is_empty() and
            self.connected
        )

    def close_when_done(self):
        "automatically close this channel once the outgoing queue is empty"
        self.producer_fifo.push(None)

    # refill the outgoing buffer by calling the more() method
    # of the first producer in the queue
    def refill_buffer(self):
        while 1:
            if len(self.producer_fifo):
                p = self.producer_fifo.first()
                # a 'None' in the producer fifo is a sentinel,
                # telling us to close the channel.
                if p is None:
                    if not self.ac_out_buffer:
                        self.producer_fifo.pop()
                        try:
                            self.close()
                        except KeyError:
                            # FIXME: tends to happen sometimes, seems to
                            # be a race condition in asyncore
                            try:
                                self._fileno = None
                                self.socket.close()
                            except:
                                pass
                    return
                elif isinstance(p, str):
                    self.producer_fifo.pop()
                    self.ac_out_buffer = self.ac_out_buffer + p
                    return
                data = p.more()
                if data:
                    self.ac_out_buffer = self.ac_out_buffer + data
                    return
                else:
                    self.producer_fifo.pop()
            else:
                return

    def initiate_send(self):
        obs = self.ac_out_buffer_size
        # try to refill the buffer
        if (len(self.ac_out_buffer) < obs):
            self.refill_buffer()

        if self.ac_out_buffer and self.connected:
            # try to send the buffer
            try:
                num_sent = self.send(self.ac_out_buffer[:obs])
                if num_sent:
                    self.ac_out_buffer = self.ac_out_buffer[num_sent:]

            except socket.error, why:
                self.handle_error()
                return

    def discard_buffers(self):
        # Emergencies only!
        self.ac_in_buffer = ''
        self.ac_out_buffer = ''
        while self.producer_fifo:
            self.producer_fifo.pop()


class fifo:

    def __init__(self, list=None):
        if not list:
            self.list = []
        else:
            self.list = list

    def __len__(self):
        return len(self.list)

    def is_empty(self):
        return self.list == []

    def first(self):
        return self.list[0]

    def push(self, data):
        self.list.append(data)

    def pop(self):
        if self.list:
            return (1, self.list.pop(0))
        else:
            return (0, None)

# Given 'haystack', see if any prefix of 'needle' is at its end.  This
# assumes an exact match has already been checked.  Return the number of
# characters matched.
# for example:
# f_p_a_e ("qwerty\r", "\r\n") => 1
# f_p_a_e ("qwertydkjf", "\r\n") => 0
# f_p_a_e ("qwerty\r\n", "\r\n") => <undefined>

# this could maybe be made faster with a computed regex?
# [answer: no; circa Python-2.0, Jan 2001]
# new python:   28961/s
# old python:   18307/s
# re:        12820/s
# regex:     14035/s


def find_prefix_at_end(haystack, needle):
    l = len(needle) - 1
    while l and not haystack.endswith(needle[:l]):
        l -= 1
    return l


class counter:

    "general-purpose counter"

    def __init__(self, initial_value=0):
        self.value = initial_value

    def increment(self, delta=1):
        result = self.value
        try:
            self.value = self.value + delta
        except OverflowError:
            self.value = long(self.value) + delta
        return result

    def decrement(self, delta=1):
        result = self.value
        try:
            self.value = self.value - delta
        except OverflowError:
            self.value = long(self.value) - delta
        return result

    def as_long(self):
        return long(self.value)

    def __nonzero__(self):
        return self.value != 0

    def __repr__(self):
        return '<counter value=%s at %x>' % (self.value, id(self))

    def __str__(self):
        s = ustr(long(self.value))
        if s[-1:] == 'L':
            s = s[:-1]
        return s


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

rfc822_reg = re.compile(rfc822_date)


def unpack_rfc822(m):
    g = m.group
    a = string.atoi
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

rfc850_reg = re.compile(rfc850_date)
# they actually unpack the same way


def unpack_rfc850(m):
    g = m.group
    a = string.atoi
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
    return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(when))

time_offset = 0


def parse_http_date(d):
    global time_offset
    d = string.lower(d)
    tz = time.timezone
    m = rfc850_reg.match(d)
    if m and m.end() == len(d):
        retval = int(time.mktime(unpack_rfc850(m)) - tz)
    else:
        m = rfc822_reg.match(d)
        if m and m.end() == len(d):
            try:
                retval = int(time.mktime(unpack_rfc822(m)) - tz)
            except OverflowError:
                return 0
        else:
            return 0
    # Thanks to Craig Silverstein <csilvers@google.com> for pointing
    # out the DST discrepancy
    if time.daylight and time.localtime(retval)[-1] == 1:  # DST correction
        retval = retval + (tz - time.altzone)
    return retval - time_offset


def check_date():
    global time_offset
    tmpfile = join_paths(GLOBAL_TEMP_DIR, "datetest" + ustr(random.random()) + ".tmp")
    open(tmpfile, "wb").close()
    time1 = os.stat(tmpfile)[stat.ST_MTIME]
    os.unlink(tmpfile)
    time2 = parse_http_date(build_http_date(time.time()))
    time_offset = time2 - time1

# producers


class simple_producer:

    "producer for a string"

    def __init__(self, data, buffer_size=1024):
        self.data = data
        self.buffer_size = buffer_size

    def more(self):
        if len(self.data) > self.buffer_size:
            result = self.data[:self.buffer_size]
            self.data = self.data[self.buffer_size:]
            return result
        else:
            result = self.data
            self.data = ''
            return result


class file_producer:

    "producer wrapper for file[-like] objects"

    # match http_channel's outgoing buffer size
    out_buffer_size = 1 << 16

    def __init__(self, file):
        self.done = 0
        self.file = file

    def more(self):
        if self.done:
            return ''
        else:
            data = self.file.read(self.out_buffer_size)
            if not data:
                self.file.close()
                del self.file
                self.done = 1
                return ''
            else:
                return data

# A simple output producer.  This one does not [yet] have
# the safety feature builtin to the monitor channel:  runaway
# output will not be caught.

# don't try to print from within any of the methods
# of this object.


class output_producer:

    "Acts like an output file; suitable for capturing sys.stdout"

    def __init__(self):
        self.data = ''

    def write(self, data):
        lines = string.splitfields(data, '\n')
        data = string.join(lines, '\r\n')
        self.data = self.data + data

    def writeline(self, line):
        self.data = self.data + line + '\r\n'

    def writelines(self, lines):
        self.data = self.data + string.joinfields(
            lines,
            '\r\n'
        ) + '\r\n'

    def flush(self):
        pass

    def softspace(self, *args):
        pass

    def more(self):
        if self.data:
            result = self.data[:512]
            self.data = self.data[512:]
            return result
        else:
            return ''


class composite_producer:

    "combine a fifo of producers into one"

    def __init__(self, producers):
        self.producers = producers

    def more(self):
        while len(self.producers):
            p = self.producers[0]
            d = p.more()
            if d:
                return d
            else:
                self.producers.pop(0)
        else:
            return ''


class globbing_producer:

    """
    'glob' the output from a producer into a particular buffer size.
    helps reduce the number of calls to send().  [this appears to
    gain about 30% performance on requests to a single channel]
    """

    def __init__(self, producer, buffer_size=1 << 16):
        self.producer = producer
        self.buffer = ''
        self.buffer_size = buffer_size

    def more(self):
        while len(self.buffer) < self.buffer_size:
            data = self.producer.more()
            if data:
                self.buffer = self.buffer + data
            else:
                break
        r = self.buffer
        self.buffer = ''
        return r


class hooked_producer:

    """
    A producer that will call <function> when it empties,.
    with an argument of the number of bytes produced.  Useful
    for logging/instrumentation purposes.
    """

    def __init__(self, producer, function):
        self.producer = producer
        self.function = function
        self.bytes = 0

    def more(self):
        if self.producer:
            result = self.producer.more()
            if not result:
                self.producer = None
                self.function(self.bytes)
            else:
                self.bytes = self.bytes + len(result)
            return result
        else:
            return ''

# HTTP 1.1 emphasizes that an advertised Content-Length header MUST be
# correct.  In the face of Strange Files, it is conceivable that
# reading a 'file' may produce an amount of data not matching that
# reported by os.stat() [text/binary mode issues, perhaps the file is
# being appended to, etc..]  This makes the chunked encoding a True
# Blessing, and it really ought to be used even with normal files.
# How beautifully it blends with the concept of the producer.


class chunked_producer:

    """A producer that implements the 'chunked' transfer coding for HTTP/1.1.
    Here is a sample usage:
            request['Transfer-Encoding'] = 'chunked'
            request.push (
                    producers.chunked_producer (your_producer)
                    )
            request.done()
    """

    def __init__(self, producer, footers=None):
        self.producer = producer
        self.footers = footers

    def more(self):
        if self.producer:
            data = self.producer.more()
            if data:
                return '%x\r\n%s\r\n' % (len(data), data)
            else:
                self.producer = None
                if self.footers:
                    return string.join(
                        ['0'] + self.footers,
                        '\r\n'
                    ) + '\r\n\r\n'
                else:
                    return '0\r\n\r\n'
        else:
            return ''


class escaping_producer:

    "A producer that escapes a sequence of characters"
    " Common usage: escaping the CRLF.CRLF sequence in SMTP, NNTP, etc..."

    def __init__(self, producer, esc_from='\r\n.', esc_to='\r\n..'):
        self.producer = producer
        self.esc_from = esc_from
        self.esc_to = esc_to
        self.buffer = ''
        self.find_prefix_at_end = find_prefix_at_end

    def more(self):
        esc_from = self.esc_from
        esc_to = self.esc_to

        buffer = self.buffer + self.producer.more()

        if buffer:
            buffer = string.replace(buffer, esc_from, esc_to)
            i = self.find_prefix_at_end(buffer, esc_from)
            if i:
                # we found a prefix
                self.buffer = buffer[-i:]
                return buffer[:-i]
            else:
                # no prefix, return it all
                self.buffer = ''
                return buffer
        else:
            return buffer


def html_repr(object):
    so = escape(repr(object))
    if hasattr(object, 'hyper_respond'):
        return '<a href="/status/object/%d/">%s</a>' % (id(object), so)
    else:
        return so


def html_reprs(list, front='', back=''):
    reprs = map(
        lambda x, f=front, b=back: '%s%s%s' % (f, x, b),
        map(lambda x: escape(html_repr(x)), list)
    )
    reprs.sort()
    return reprs

# for example, tera, giga, mega, kilo
# p_d (n, (1024, 1024, 1024, 1024))
# smallest divider goes first - for example
# minutes, hours, days
# p_d (n, (60, 60, 24))


def progressive_divide(n, parts):
    result = []
    for part in parts:
        n, rem = divmod(n, part)
        result.append(rem)
    result.append(n)
    return result

# b,k,m,g,t


def split_by_units(n, units, dividers, format_string):
    divs = progressive_divide(n, dividers)
    result = []
    for i in range(len(units)):
        if divs[i]:
            result.append(format_string % (divs[i], units[i]))
    result.reverse()
    if not result:
        return [format_string % (0, units[0])]
    else:
        return result


def english_bytes(n):
    return split_by_units(
        n,
        ('', 'K', 'M', 'G', 'T'),
        (1024, 1024, 1024, 1024, 1024),
        '%d %sB'
    )


def english_time(n):
    return split_by_units(
        n,
        ('secs', 'mins', 'hours', 'days', 'weeks', 'years'),
        (60,     60,      24,     7,       52),
        '%d %s'
    )


def strip_eol(line):
    while line and line[-1] in '\r\n':
        line = line[:-1]
    return line

VERSION_STRING = string.split(RCS_ID)[2]
ATHANA_VERSION = "0.2.1"

# ===========================================================================
#                                                       Request Object
# ===========================================================================


class http_request(object):

    # default reply code
    reply_code = 200

    request_counter = counter()

    # Whether to automatically use chunked encoding when
    #
    #   HTTP version is 1.1
    #   Content-Length is not set
    #   Chunked encoding is not already in effect
    #
    # If your clients are having trouble, you might want to disable this.
    use_chunked = 1

    # by default, this request object ignores user data.
    collector = None

    def __init__(self, *args):
        # unpack information about the request
        (self.channel, self.request,
         self.command, self.uri, self.version,
         self.header) = args

        self.method = self.command
        self.outgoing = []
        self.reply_headers = {
            'Server': 'Athana/%s' % ATHANA_VERSION,
            'Date': build_http_date(time.time()),
        }
        self.request_number = http_request.request_counter.increment()
        self._split_uri = None
        self._header_cache = {}
        self.session = None
        
        # XXX: not really a good idea, but we need some place to store request-bound caching data...
        self.app_cache = {}

    # --------------------------------------------------
    # reply header management
    # --------------------------------------------------
    def __setitem__(self, key, value):
        try:
            if key == 'Set-Cookie':
                self.reply_headers[key] += [value]
            else:
                self.reply_headers[key] = [value]
        except:
            self.reply_headers[key] = [value]

    def __getitem__(self, key):
        return self.reply_headers[key][0]

    def has_key(self, key):
        return self.reply_headers.has_key(key)

    def build_reply_header(self):
        h = []
        for k, vv in self.reply_headers.items():
            if not isinstance(vv, list):
                if isinstance(k, unicode):
                    k = k.encode("utf8")
                if isinstance(vv, unicode):
                    vv = vv.encode("utf8")
                h += ["%s: %s" % (k, vv)]
            else:
                for v in vv:
                    if isinstance(k, unicode):
                        k = k.encode("utf8")
                    if isinstance(v, unicode):
                        v = v.encode("utf8")
                    h += ["%s: %s" % (k, v)]
        return string.join([self.response(self.reply_code)] + h, '\r\n') + '\r\n\r\n'

    # --------------------------------------------------
    # split a uri
    # --------------------------------------------------

    # <path>;<params>?<query>#<fragment>
    path_regex = re.compile(
        #      path      params    query   fragment
        r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?'
    )

    def split_uri(self):
        if self._split_uri is None:
            m = self.path_regex.match(self.uri)
            if m.end() != len(self.uri):
                raise ValueError("Broken URI")
            else:
                self._split_uri = m.groups()
        return self._split_uri

    def get_header_with_regex(self, head_reg, group):
        for line in self.header:
            m = head_reg.match(line)
            if m.end() == len(line):
                return m.group(group)
        return ''

    def get_header(self, header):
        header = string.lower(header)
        hc = self._header_cache
        if not hc.has_key(header):
            h = header + ': '
            hl = len(h)
            for line in self.header:
                if string.lower(line[:hl]) == h:
                    r = line[hl:]
                    hc[header] = r
                    return r
            hc[header] = None
            return None
        else:
            return hc[header]

    @cached_property
    def accept_mimetypes(self):
        accept = parse_accept_header(self.get_header("ACCEPT"), MIMEAccept)
        return accept

    # --------------------------------------------------
    # user data
    # --------------------------------------------------

    def collect_incoming_data(self, data):
        if self.collector:
            self.collector.collect_incoming_data(data)
        else:
            logg.warn('Dropping %d bytes of incoming request data', len(data))

    def found_terminator(self):
        if self.collector:
            self.collector.found_terminator()
        else:
            logg.warn('Unexpected end-of-record for incoming request')

    def push(self, thing):
        if type(thing) == type(''):
            self.outgoing.append(simple_producer(thing))
        else:
            thing.more
            self.outgoing.append(thing)

    def response(self, code=200):
        message = self.responses[code]
        self.reply_code = code
        return 'HTTP/%s %d %s' % (self.version, code, message)

    def error(self, code, s=None, content_type='text/html'):
        self.reply_code = code
        self.outgoing = []
        message = self.responses[code]
        if s is None:
            s = self.DEFAULT_ERROR_MESSAGE % {
                'code': code,
                'message': message,
            }
        self['Content-Length'] = len(s)
        self['Content-Type'] = content_type
        # make an error reply
        self.push(s)
        self.done()

    # can also be used for empty replies
    reply_now = error

    def unlink_tempfiles(self):
        unlinked_tempfiles = []
        if hasattr(self, "tempfiles"):
            for f in self.tempfiles:
                os.unlink(f)
                unlinked_tempfiles.append(f)
                logg.debug("unlinked tempfile %s", f)
        return unlinked_tempfiles

    def done(self):
        "finalize this transaction - send output to the http channel"

        self.unlink_tempfiles()

        # ----------------------------------------
        # persistent connection management
        # ----------------------------------------

        #  --- BUCKLE UP! ----

        connection = string.lower(get_header(CONNECTION, self.header))

        close_it = 0
        wrap_in_chunking = 0

        if self.version == '1.0':
            if connection == 'keep-alive':
                if not self.has_key('Content-Length'):
                    close_it = 1
                else:
                    self['Connection'] = 'Keep-Alive'
            else:
                close_it = 1
        elif self.version == '1.1':
            if connection == 'close':
                close_it = 1
            elif not self.has_key('Content-Length'):
                if self.has_key('Transfer-Encoding'):
                    if not self['Transfer-Encoding'] == 'chunked':
                        close_it = 1
                elif self.use_chunked:
                    self['Transfer-Encoding'] = 'chunked'
                    wrap_in_chunking = 1
                else:
                    close_it = 1
        elif self.version is None:
            # Although we don't *really* support http/0.9 (because we'd have to
            # use \r\n as a terminator, and it would just yuck up a lot of stuff)
            # it's very common for developers to not want to type a version number
            # when using telnet to debug a server.
            close_it = 1

        if self.session and "PSESSION" not in self.Cookies:
            self.setCookie('PSESSION', self.sessionid, path="/", secure=config.getboolean("host.ssl", True))
            
        if "Cache-Control" not in self.reply_headers:
            self.reply_headers["Cache-Control"] = "no-cache"

        reply_header = self.build_reply_header()

        outgoing_header = simple_producer(reply_header)

        if close_it:
            self['Connection'] = 'close'

        if wrap_in_chunking:
            outgoing_producer = chunked_producer(
                composite_producer(list(self.outgoing))
            )
            # prepend the header
            outgoing_producer = composite_producer(
                [outgoing_header, outgoing_producer]
            )
        else:
            # prepend the header
            self.outgoing.insert(0, outgoing_header)
            outgoing_producer = composite_producer(list(self.outgoing))

        # actually, this is already set to None by the handler:
        self.channel.current_request = None

        # apply a few final transformations to the output
        self.channel.push_with_producer(
            # globbing gives us large packets
            globbing_producer(
                outgoing_producer
            )
        )

        if close_it:
            self.channel.close_when_done()

    def log(self):
        logg.info('%s:%s - - %s "%s"', self.channel.addr[0], self.channel.addr[1],
                  time.strftime('[%d/%b/%Y:%H:%M:%S ]', time.gmtime()), self.request)

    def write(self, text):
        if isinstance(text, unicode):
            self.push(text.encode("utf-8"))
        elif isinstance(text, str):
            self.push(text)
        else:
            text.more
            self.push(text)

    def setStatus(self, status):
        self.reply_code = status

    def makeLink(self, page, params=None):
        query = ""
        if params is not None:
            first = 1
            for k, v in params.items():
                if first:
                    query += "?"
                else:
                    query += "&"
                query += "{}={}".format(urllib.quote(k), urllib.quote(unicode(v)))
                first = 0
        return "{}{}".format(page, query)

    def sendFile(self, path, content_type, force=0):
        
        if isinstance(path, unicode):
            path = path.encode("utf8")
        
        if isinstance(content_type, unicode):
            content_type = content_type.encode("utf8")
        

        x_accel_redirect = config.get("nginx.X-Accel-Redirect", "").lower() == "true"
        file = None
        file_length = 0

        if not x_accel_redirect:
            try:
                file_length = os.stat(path)[stat.ST_SIZE]
            except OSError:
                self.error(404)
                return

        ims = get_header_match(IF_MODIFIED_SINCE, self.header)
        length_match = 1
        if ims:
            length = ims.group(4)
            if length:
                try:
                    length = string.atoi(length)
                    if length != file_length:
                        length_match = 0
                except:
                    pass
        ims_date = 0
        if ims:
            ims_date = parse_http_date(ims.group(1))

        try:
            mtime = os.stat(path)[stat.ST_MTIME]
        except:
            self.error(404)
            return
        if length_match and ims_date:
            if mtime <= ims_date and not force:
                # print "File "+path+" was not modified since "+ustr(ims_date)+" (current filedate is "+ustr(mtime)+")-> 304"
                self.reply_code = 304
                return

        if not x_accel_redirect:
            try:
                file = open(path, 'rb')
            except IOError:
                self.error(404)
                print "404"
                return

        self.reply_headers['Last-Modified'] = build_http_date(mtime)
        self.reply_headers['Content-Length'] = file_length
        self.reply_headers['Content-Type'] = content_type
        if x_accel_redirect:
            self.reply_headers['X-Accel-Redirect'] = path
        if self.command == 'GET':
            if x_accel_redirect:
                self.done()
            else:
                self.push(file_producer(file))
        return

    def sendAsBuffer(self, text, content_type, force=0, allow_cross_origin=False):
        from StringIO import StringIO
        stringio = StringIO(text)

        try:
            file_length = len(stringio.buf)
        except OSError:
            self.error(404)
            return

        ims = get_header_match(IF_MODIFIED_SINCE, self.header)
        length_match = 1
        if ims:
            length = ims.group(4)
            if length:
                try:
                    length = string.atoi(length)
                    if length != file_length:
                        length_match = 0
                except:
                    pass
        ims_date = 0
        if ims:
            ims_date = parse_http_date(ims.group(1))

        try:
            import time
            mtime = time.time()  # os.stat (path)[stat.ST_MTIME]
        except:
            self.error(404)
            return
        if length_match and ims_date:
            if mtime <= ims_date and not force:
                self.reply_code = 304
                return
        try:
            file = stringio
        except IOError:
            self.error(404)
            return

        self.reply_headers['Last-Modified'] = build_http_date(mtime)
        self.reply_headers['Content-Length'] = file_length
        self.reply_headers['Content-Type'] = content_type
        if allow_cross_origin:
            self.reply_headers['Access-Control-Allow-Origin'] = '*'
        if self.command == 'GET':
            self.push(file_producer(file))
        return

    def setCookie(self, name, value, expire=None, path=None, http_only=True, secure=False):
        
        parts = [name + '=' + value]

        if expire:
            datestr = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime(expire))
            parts.append('expires=' + datestr)
            
        if path:
            parts.append("path=" + path)

        if http_only:
            parts.append("HttpOnly")
            
        if secure:
            parts.append("Secure")
            
        cookie_str = "; ".join(parts)

        if 'Set-Cookie' not in self.reply_headers:
            self.reply_headers['Set-Cookie'] = [cookie_str]
        else:
            self.reply_headers['Set-Cookie'] += [cookie_str]

    def makeSelfLink(self, params):
        params2 = self.params.copy()
        for k, v in params.items():
            if v is not None:
                params2[k] = v
            else:
                try:
                    del params2[k]
                except:
                    pass
        ret = self.makeLink(self.fullpath, params2)
        return ret

    def writeTAL(self, page, context, macro=None):
        tal.runTAL(self, context, file=page, macro=macro, request=self)

    def writeTALstr(self, string, context, macro=None):
        tal.runTAL(self, context, string=string, macro=macro, request=self)

    def getTAL(self, page, context, macro=None):
        return tal.processTAL(context, file=page, macro=macro, request=self)

    def getTALstr(self, string, context, macro=None):
        return tal.processTAL(context, string=string, macro=macro, request=self)

    # COMPAT: new param style like flask
    def make_legacy_params_dict(self):
        """convert new-style params to old style athana params dict"""
        self.params = params = {}
        for key, values in chain(self.form.iterlists(), self.args.iterlists()):
            value = ";".join(values)
            params[key] = value
#             params[key.encode("utf8")] = value.encode("utf8")
        params.update(self.files.iteritems())

    # COMPAT: flask-style properties
    @property
    def remote_addr(self):
        return self.ip

    responses = {
        100: "Continue",
        101: "Switching Protocols",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Moved Temporarily",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Time-out",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Request Entity Too Large",
        414: "Request-URI Too Large",
        415: "Unsupported Media Type",
        418: "I'm a Teapot",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Time-out",
        505: "HTTP Version not supported"
    }

    # Default error message
    DEFAULT_ERROR_MESSAGE = string.join(
        ['<html><head>',
         '<title>Error response</title>',
         '</head>',
         '<body>',
         '<h1>Error response</h1>',
         '<p>Error code %(code)d.</p>',
         '<p>Message: %(message)s.</p>',
         '</body></html>',
         ''
         ],
        '\r\n'
    )


# ===========================================================================
#                                                HTTP Channel Object
# ===========================================================================

class http_channel (async_chat):

    # use a larger default output buffer
    ac_out_buffer_size = 1 << 16

    current_request = None
    channel_counter = counter()

    def __init__(self, server, conn, addr):
        self.channel_number = http_channel.channel_counter.increment()
        self.request_counter = counter()
        async_chat.__init__(self, conn)
        self.server = server
        self.addr = addr
        self.set_terminator('\r\n\r\n')
        self.in_buffer = ''
        self.creation_time = int(time.time())
        self.check_maintenance()
        self.producer_lock = thread.allocate_lock()

    def initiate_send(self):
        self.producer_lock.acquire()
        try:
            async_chat.initiate_send(self)
        finally:
            self.producer_lock.release()

    def push(self, data):
        data.more
        self.producer_lock.acquire()
        try:
            self.producer_fifo.push(simple_producer(data))
        finally:
            self.producer_lock.release()
        self.initiate_send()

    def push_with_producer(self, producer):
        self.producer_lock.acquire()
        try:
            self.producer_fifo.push(producer)
        finally:
            self.producer_lock.release()
        self.initiate_send()

    def close_when_done(self):
        self.producer_lock.acquire()
        try:
            self.producer_fifo.push(None)
        finally:
            self.producer_lock.release()

        # results in select.error: (9, 'Bad file descriptor') if the socket map is poll'ed
        # while this socket is being closed
        # we do it anyway, and catch the select.error in the main loop

        # XXX on Ubuntu's 2.6.10-5-386, the socket won't be closed until the select finishes (or
        # times out). We probably need to send a SIGINT signal or something. For now, we just
        # set a very small timeout (0.01) in the main loop, so that select() will be called often
        # enough.

        # it also results in a "NoneType has no attribute more" error if refill_buffer tries
        # to run data = p.more() on the None terminator (which we catch)
        try:
            self.initiate_send()
        except AttributeError:
            pass

    def __repr__(self):
        ar = async_chat.__repr__(self)[1:-1]
        return '<%s channel#: %s requests:%s>' % (
            ar,
            self.channel_number,
            self.request_counter
        )

    # Channel Counter, Maintenance Interval...
    maintenance_interval = 500

    def check_maintenance(self):
        if not self.channel_number % self.maintenance_interval:
            self.maintenance()

    def maintenance(self):
        self.kill_zombies()

    # 30-minute zombie timeout.  status_handler also knows how to kill zombies.
    zombie_timeout = 30 * 60

    def kill_zombies(self):
        now = int(time.time())
        for channel in asyncore.socket_map.values():
            if channel.__class__ == self.__class__:
                if (now - channel.creation_time) > channel.zombie_timeout:
                    channel.close()

    # --------------------------------------------------
    # send/recv overrides, good place for instrumentation.
    # --------------------------------------------------

    # this information needs to get into the request object,
    # so that it may log correctly.
    def send(self, data):
        result = 0
        try:
            result = async_chat.send(self, data)
        except:
            pass
        self.server.bytes_out.increment(len(data))
        return result

    def recv(self, buffer_size):
        try:
            result = async_chat.recv(self, buffer_size)
            self.server.bytes_in.increment(len(result))
            return result
        except MemoryError:
            # --- Save a Trip to Your Service Provider ---
            # It's possible for a process to eat up all the memory of
            # the machine, and put it in an extremely wedged state,
            # where medusa keeps running and can't be shut down.  This
            # is where MemoryError tends to get thrown, though of
            # course it could get thrown elsewhere.
            sys.exit("Out of Memory!")

    def handle_error(self):
        logg.exception("uncaught exception in http_channel")
        t, v = sys.exc_info()[:2]
        if hasattr(self, "current_request") and self.current_request:
            unlinked_tempfiles = self.current_request.unlink_tempfiles()
            if unlinked_tempfiles:
                logg.warn("POSSIBLE ATTACK! tempfiles were still open, closed %s files", len(unlinked_tempfiles))
        if t is SystemExit:
            raise t(v)
        else:
            async_chat.handle_error(self)

    def log(self, *args):
        pass

    # --------------------------------------------------
    # async_chat methods
    # --------------------------------------------------

    def collect_incoming_data(self, data):
        if self.current_request:
            # we are receiving data (probably POST data) for a request
            self.current_request.collect_incoming_data(data)
        else:
            # we are receiving header (request) data
            self.in_buffer = self.in_buffer + data

    def found_terminator(self):
        if self.current_request:
            self.current_request.found_terminator()
        else:
            header = self.in_buffer
            self.in_buffer = ''
            lines = string.split(header, '\r\n')

            # --------------------------------------------------
            # crack the request header
            # --------------------------------------------------

            while lines and not lines[0]:
                # as per the suggestion of http-1.1 section 4.1, (and
                # Eric Parker <eparker@zyvex.com>), ignore a leading
                # blank lines (buggy browsers tack it onto the end of
                # POST requests)
                lines = lines[1:]

            if not lines:
                self.close_when_done()
                return

            request = lines[0]

            command, uri, version = crack_request(request)
            header = join_headers(lines[1:])

            # unquote path if necessary (thanks to Skip Montanaro for pointing
            # out that we must unquote in piecemeal fashion).
            rpath, rquery = splitquery(uri)
            if '%' in rpath:
                if rquery:
                    uri = unquote(rpath) + '?' + rquery
                else:
                    uri = unquote(rpath)

            r = http_request(self, request, command, uri, version, header)
            self.request_counter.increment()
            self.server.total_requests.increment()

            if command is None:
                logg.error('Bad HTTP request: %s', repr(request))
                r.error(400)
                return

            # --------------------------------------------------
            # handler selection and dispatch
            # --------------------------------------------------
            for h in self.server.handlers:
                if h.match(r):
                    try:
                        self.current_request = r
                        # This isn't used anywhere.
                        # r.handler = h # CYCLE
                        h.handle_request(r)
                    except:
                        self.server.exceptions.increment()
                        (file, fun, line), t, v, tbinfo = asyncore.compact_traceback()
                        logg.error('Server Error: %s, %s: file: %s line: %s', t, v, file, line, exc_info=1)
                        try:
                            r.error(500)
                        except:
                            pass
                    return

            # no handlers, so complain
            r.error(404)

# ===========================================================================
#                                                HTTP Server Object
# ===========================================================================


class http_server (asyncore.dispatcher):

    SERVER_IDENT = 'HTTP Server (V%s)' % VERSION_STRING

    channel_class = http_channel

    def __init__(self, host, port, resolver=None):
        self.ip = self.host = host
        self.port = port
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        self.handlers = []

        self.set_reuse_addr()
        self.bind((host, port))

        # lower this to 5 if your OS complains
        self.listen(1024)

        self.server_name = host
        self.server_port = port
        self.total_clients = counter()
        self.total_requests = counter()
        self.exceptions = counter()
        self.bytes_out = counter()
        self.bytes_in = counter()

        logg.info('Athana HTTP Server started at http://%s:%d', self.server_name, port)
    # overriding asyncore.dispatcher methods

    # cheap inheritance, used to pass all other attribute
    # references to the underlying socket object.
    def __getattr__(self, attr):
        try:
            retattr = getattr(self.socket, attr)
        except AttributeError:
            logg.error("http_server instance has no attribute '%s'", attr)
            raise
        else:
            msg = "%(me)s.%(attr)s is deprecated. Use %(me)s.socket.%(attr)s " \
                  "instead." % {'me': self.__class__.__name__, 'attr': attr}
            logg.warn(msg)
            return retattr

    def log(self, message):
        logg.debug(message)

    def log_info(self, message, type='info'):
        logg.info(message)

    def writable(self):
        return 0

    def handle_read(self):
        pass

    def readable(self):
        return self.accepting

    def handle_connect(self):
        pass

    def handle_accept(self):
        self.total_clients.increment()
        try:
            conn, addr = self.accept()
        except socket.error:
            # linux: on rare occasions we get a bogus socket back from
            # accept.  socketmodule.c:makesockaddr complains that the
            # address family is unknown.  We don't want the whole server
            # to shut down because of this.
            logg.error('warning: server accept() threw an exception', exc_info=1)
            return
        except TypeError:
            # unpack non-sequence.  this can happen when a read event
            # fires on a listening socket, but when we call accept()
            # we get EWOULDBLOCK, so dispatcher.accept() returns None.
            # Seen on FreeBSD3.
            logg.error('warning: server accept() threw EWOULDBLOCK', exc_info=1)
            return

        self.channel_class(self, conn, addr)

    def install_handler(self, handler, back=0):
        if back:
            self.handlers.append(handler)
        else:
            self.handlers.insert(0, handler)

    def remove_handler(self, handler):
        self.handlers.remove(handler)


CONNECTION = re.compile('Connection: (.*)', re.IGNORECASE)

# merge multi-line headers
# [486dx2: ~500/sec]


def join_headers(headers):
    r = []
    for i in range(len(headers)):
        if headers[i][0] in ' \t':
            r[-1] = r[-1] + headers[i][1:]
        else:
            r.append(headers[i])
    return r


def get_header(head_reg, lines, group=1):
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

REQUEST = re.compile('([^ ]+) ([^ ]+)(( HTTP/([0-9.]+))$|$)')


def crack_request(r):
    m = REQUEST.match(r)
    if m and m.end() == len(r):
        if m.group(3):
            version = m.group(5)
        else:
            version = None
        return m.group(1), m.group(2), version
    else:
        return None, None, None


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

    default_file_producer = file_producer

    def __init__(self, filesystem):
        self.filesystem = filesystem
        # count total hits
        self.hit_counter = counter()
        # count file deliveries
        self.file_counter = counter()
        # count cache hits
        self.cache_counter = counter()

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
        path, params, query, fragment = request.split_uri()
        if '%' in path:
            path = unquote(path)
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
            request.error(400)  # bad request
            return

        self.hit_counter.increment()

        path, params, query, fragment = request.split_uri()

        if '%' in path:
            path = unquote(path)

        # strip off all leading slashes
        while path and path[0] == '/':
            path = path[1:]

        if self.filesystem.isdir(path):
            if path and path[-1] != '/':
                request['Location'] = 'http://%s/%s/' % (
                    request.channel.server.server_name,
                    path
                )
                request.error(301)
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
                request.error(404)  # Not Found
                return

        elif not self.filesystem.isfile(path):
            request.error(404)  # Not Found
            return

        file_length = self.filesystem.stat(path)[stat.ST_SIZE]

        ims = get_header_match(IF_MODIFIED_SINCE, request.header)

        length_match = 1
        if ims:
            length = ims.group(4)
            if length:
                try:
                    length = string.atoi(length)
                    if length != file_length:
                        length_match = 0
                except:
                    pass

        ims_date = 0

        if ims:
            ims_date = parse_http_date(ims.group(1))

        try:
            mtime = self.filesystem.stat(path)[stat.ST_MTIME]
        except:
            request.error(404)
            return

        if length_match and ims_date:
            if mtime <= ims_date:
                request.reply_code = 304
                request.done()
                self.cache_counter.increment()
                # print "File "+path+" was not modified since "+ustr(ims_date)+" (current filedate is "+ustr(mtime)+")"
                return
        try:
            file = self.filesystem.open(path, 'rb')
        except IOError:
            request.error(404)
            return

        request['Last-Modified'] = build_http_date(mtime)
        request['Content-Length'] = file_length
        self.set_content_type(path, request)

        if request.command == 'GET':
            request.push(self.default_file_producer(file))

        self.file_counter.increment()
        request.done()

    def set_content_type(self, path, request):
        ext = string.lower(get_extension(path))
        typ, encoding = mimetypes.guess_type(path)
        if typ is not None:
            request['Content-Type'] = typ
        else:
            # TODO: test a chunk off the front of the file for 8-bit
            # characters, and use application/octet-stream instead.
            request['Content-Type'] = 'text/plain'

    def status(self):
        return simple_producer(
            '<li>%s' % html_repr(self)
            + '<ul>'
            + '  <li><b>Total Hits:</b> %s' % self.hit_counter
            + '  <li><b>Files Delivered:</b> %s' % self.file_counter
            + '  <li><b>Cache Hits:</b> %s' % self.cache_counter
            + '</ul>'
        )

# HTTP/1.0 doesn't say anything about the "; length=nnnn" addition
# to this header.  I suppose its purpose is to avoid the overhead
# of parsing dates...
IF_MODIFIED_SINCE = re.compile(
    'If-Modified-Since: ([^;]+)((; length=([0-9]+)$)|$)',
    re.IGNORECASE
)

USER_AGENT = re.compile('User-Agent: (.*)', re.IGNORECASE)

CONTENT_TYPE = re.compile(
    r'Content-Type: ([^;]+)((; boundary=([A-Za-z0-9\'\(\)+_,./:=?-]+)$)|$)',
    re.IGNORECASE
)

get_header = get_header
get_header_match = get_header_match


def get_extension(path):
    dirsep = string.rfind(path, '/')
    dotsep = string.rfind(path, '.')
    if dotsep > dirsep:
        return path[dotsep + 1:]
    else:
        return ''


class abstract_filesystem:

    def __init__(self):
        pass

    def current_directory(self):
        "Return a string representing the current directory."
        pass

    def listdir(self, path, long=0):
        """Return a listing of the directory at 'path' The empty string
        indicates the current directory.  If 'long' is set, instead
        return a list of (name, stat_info) tuples
        """
        pass

    def open(self, path, mode):
        "Return an open file object"
        pass

    def stat(self, path):
        "Return the equivalent of os.stat() on the given path."
        pass

    def isdir(self, path):
        "Does the path represent a directory?"
        pass

    def isfile(self, path):
        "Does the path represent a plain file?"
        pass

    def cwd(self, path):
        "Change the working directory."
        pass

    def cdup(self):
        "Change to the parent of the current directory."
        pass

    def longify(self, path):
        """Return a 'long' representation of the filename
        [for the output of the LIST command]"""
        pass

# standard wrapper around a unix-like filesystem, with a 'false root'
# capability.

# security considerations: can symbolic links be used to 'escape' the
# root?  should we allow it?  if not, then we could scan the
# filesystem on startup, but that would not help if they were added
# later.  We will probably need to check for symlinks in the cwd method.

# what to do if wd is an invalid directory?


def safe_stat(path):
    try:
        return (path, os.stat(path))
    except:
        return None


class os_filesystem:
    path_module = os.path

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
            old_dir = os.getcwd()
            # temporarily change to that directory, in order
            # to see if we have permission to do so.
            try:
                can = 0
                try:
                    os.chdir(translated_path)
                    can = 1
                    self.wd = p
                except:
                    pass
            finally:
                if can:
                    os.chdir(old_dir)
            return can

    def cdup(self):
        return self.cwd('..')

    def listdir(self, path, long=0):
        p = self.translate(path)
        # I think we should glob, but limit it to the current
        # directory only.
        ld = os.listdir(p)
        if not long:
            return list_producer(ld, None)
        else:
            old_dir = os.getcwd()
            try:
                os.chdir(p)
                # if os.stat fails we ignore that file.
                result = filter(None, map(safe_stat, ld))
            finally:
                os.chdir(old_dir)
            return list_producer(result, self.longify)

    # TODO: implement a cache w/timeout for stat()
    def stat(self, path):
        p = self.translate(path)
        return os.stat(p)

    def open(self, path, mode):
        p = self.translate(path)
        return open(p, mode)

    def unlink(self, path):
        p = self.translate(path)
        return os.unlink(p)

    def mkdir(self, path):
        p = self.translate(path)
        return os.mkdir(p)

    def rmdir(self, path):
        p = self.translate(path)
        return os.rmdir(p)

    # utility methods
    def normalize(self, path):
        # watch for the ever-sneaky '/+' path element
        path = re.sub('/+', '/', path)
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
        path = string.join(string.split(path, '/'), os.sep)
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

# this matches the output of NT's ftp server (when in
# MSDOS mode) exactly.


def msdos_longify(file, stat_info):
    if stat.S_ISDIR(stat_info[stat.ST_MODE]):
        dir = '<DIR>'
    else:
        dir = '     '
    date = msdos_date(stat_info[stat.ST_MTIME])
    return '%s       %s %8d %s' % (
        date,
        dir,
        stat_info[stat.ST_SIZE],
        file
    )


def msdos_date(t):
    try:
        info = time.gmtime(t)
    except:
        info = time.gmtime(0)
    # year, month, day, hour, minute, second, ...
    if info[3] > 11:
        merid = 'PM'
        info[3] = info[3] - 12
    else:
        merid = 'AM'
    return '%02d-%02d-%02d  %02d:%02d%s' % (
        info[1],
        info[2],
        info[0] % 100,
        info[3],
        info[4],
        merid
    )

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


def unix_longify(file, stat_info):
    # for now, only pay attention to the lower bits
    mode = ('%o' % stat_info[stat.ST_MODE])[-3:]
    mode = string.join(map(lambda x: mode_table[x], mode), '')
    if stat.S_ISDIR(stat_info[stat.ST_MODE]):
        dirchar = 'd'
    else:
        dirchar = '-'
    date = ls_date(long(time.time()), stat_info[stat.ST_MTIME])
    return '%s%s %3d %-8d %-8d %8d %s %s' % (
        dirchar,
        mode,
        stat_info[stat.ST_NLINK],
        stat_info[stat.ST_UID],
        stat_info[stat.ST_GID],
        stat_info[stat.ST_SIZE],
        date,
        file
    )

# Emulate the unix 'ls' command's date field.
# it has two formats - if the date is more than 180
# days in the past, then it's like this:
# Oct 19  1995
# otherwise, it looks like this:
# Oct 19 17:33


def ls_date(now, t):
    try:
        info = time.gmtime(t)
    except:
        info = time.gmtime(0)
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


class list_producer:

    def __init__(self, list, func=None):
        self.list = list
        self.func = func

    # this should do a pushd/popd
    def more(self):
        if not self.list:
            return ''
        else:
            # do a few at a time
            bunch = self.list[:50]
            if self.func is not None:
                bunch = map(self.func, bunch)
            self.list = self.list[50:]
            return string.joinfields(bunch, '\r\n') + '\r\n'


class hooked_callback:

    def __init__(self, hook, callback):
        self.hook, self.callback = hook, callback

    def __call__(self, *args):
        apply(self.hook, args)
        apply(self.callback, args)

# An extensible, configurable, asynchronous FTP server.
#
# All socket I/O is non-blocking, however file I/O is currently
# blocking.  Eventually file I/O may be made non-blocking, too, if it
# seems necessary.  Currently the only CPU-intensive operation is
# getting and formatting a directory listing.  [this could be moved
# into another process/directory server, or another thread?]
#
# Only a subset of RFC 959 is implemented, but much of that RFC is
# vestigial anyway.  I've attempted to include the most commonly-used
# commands, using the feature set of wu-ftpd as a guide.


# TODO: implement a directory listing cache.  On very-high-load
# servers this could save a lot of disk abuse, and possibly the
# work of computing emulated unix ls output.

# Potential security problem with the FTP protocol?  I don't think
# there's any verification of the origin of a data connection.  Not
# really a problem for the server (since it doesn't send the port
# command, except when in PASV mode) But I think a data connection
# could be spoofed by a program with access to a sniffer - it could
# watch for a PORT command to go over a command channel, and then
# connect to that port before the server does.

# Unix user id's:
# In order to support assuming the id of a particular user,
# it seems there are two options:
# 1) fork, and seteuid in the child
# 2) carefully control the effective uid around filesystem accessing
#    methods, using try/finally. [this seems to work]

VERSION = string.split(RCS_ID)[2]


class ftp_channel (async_chat):

    # defaults for a reliable __repr__
    addr = ('unknown', '0')

    # unset this in a derived class in order
    # to enable the commands in 'self.write_commands'
    read_only = 0
    write_commands = ['appe', 'dele', 'mkd', 'rmd', 'stor', 'stou']

    restart_position = 0

    # comply with (possibly troublesome) RFC959 requirements
    # This is necessary to correctly run an active data connection
    # through a firewall that triggers on the source port (expected
    # to be 'L-1', or 20 in the normal case).
    bind_local_minus_one = 1

    def __init__(self, server, conn, addr):
        self.server = server
        self.current_mode = 'a'
        self.addr = addr
        async_chat.__init__(self, conn)
        self.set_terminator('\r\n')

        # client data port.  Defaults to 'the same as the control connection'.
        self.client_addr = (addr[0], 21)

        self.client_dc = None
        self.in_buffer = ''
        self.closing = 0
        self.passive_acceptor = None
        self.passive_connection = None
        self.filesystem = None
        self.authorized = 0
        # send the greeting
        self.respond(
            '220 %s FTP server (Medusa Async V%s [experimental]) ready.' % (
                self.server.hostname,
                VERSION
            )
        )

#       def __del__ (self):
#               print 'ftp_channel.__del__()'

    # --------------------------------------------------
    # async-library methods
    # --------------------------------------------------

    def handle_expt(self):
        # this is handled below.  not sure what I could
        # do here to make that code less kludgish.
        pass

    def collect_incoming_data(self, data):
        self.in_buffer = self.in_buffer + data
        if len(self.in_buffer) > 4096:
            # silently truncate really long lines
            # (possible denial-of-service attack)
            self.in_buffer = ''

    def found_terminator(self):

        line = self.in_buffer

        if not len(line):
            return

        sp = string.find(line, ' ')
        if sp != -1:
            line = [line[:sp], line[sp + 1:]]
        else:
            line = [line]

        command = string.lower(line[0])
        # watch especially for 'urgent' abort commands.
        if string.find(command, 'abor') != -1:
            # strip off telnet sync chars and the like...
            while command and command[0] not in string.letters:
                command = command[1:]
        fun_name = 'cmd_%s' % command
        if command != 'pass':
            self.log('<== %s' % repr(self.in_buffer)[1:-1])
        else:
            self.log('<== %s' % line[0] + ' <password>')
        self.in_buffer = ''
        if not hasattr(self, fun_name):
            self.command_not_understood(line[0])
            return
        fun = getattr(self, fun_name)
        if (not self.authorized) and (command not in ('user', 'pass', 'help', 'quit')):
            self.respond('530 Please log in with USER and PASS')
        elif (not self.check_command_authorization(command)):
            self.command_not_authorized(command)
        else:
            try:
                result = apply(fun, (line,))
            except:
                self.server.total_exceptions.increment()
                (file, fun, line), t, v, tbinfo = asyncore.compact_traceback()
                if self.client_dc:
                    try:
                        self.client_dc.close()
                    except:
                        pass
                self.respond(
                    '451 Server Error: %s, %s: file: %s line: %s' % (
                        t, v, file, line,
                    )
                )

    closed = 0

    def close(self):
        if not self.closed:
            self.closed = 1
            if self.passive_acceptor:
                self.passive_acceptor.close()
            if self.client_dc:
                self.client_dc.close()
            self.server.closed_sessions.increment()
            async_chat.close(self)

    # --------------------------------------------------
    # filesystem interface functions.
    # override these to provide access control or perform
    # other functions.
    # --------------------------------------------------

    def cwd(self, line):
        return self.filesystem.cwd(line[1])

    def cdup(self, line):
        return self.filesystem.cdup()

    def rnfr(self, line):
        return self.filesystem.rnfr(line)

    def rnto(self, line):
        return self.filesystem.rnto(line)

    def open(self, path, mode):
        return self.filesystem.open(path, mode)

    # returns a producer
    def listdir(self, path, long=0):
        return self.filesystem.listdir(path, long)

    def get_dir_list(self, line, long=0):
        # we need to scan the command line for arguments to '/bin/ls'...
        args = line[1:]
        path_args = []
        for arg in args:
            if arg[0] != '-':
                path_args.append(arg)
            else:
                # ignore arguments
                pass
        if len(path_args) < 1:
            dir = '.'
        else:
            dir = path_args[0]
        return self.listdir(dir, long)

    # --------------------------------------------------
    # authorization methods
    # --------------------------------------------------

    def check_command_authorization(self, command):
        if command in self.write_commands and self.read_only:
            return 0
        else:
            return 1

    # --------------------------------------------------
    # utility methods
    # --------------------------------------------------

    def log(self, message):
        if self.filesystem and self.filesystem.debug() == 1:
            self.server.logger.log(
                self.addr[0],
                '%d %s' % (
                    self.addr[1], message
                )
            )

    def respond(self, resp):
        if self.filesystem and self.filesystem.debug() == 1:
            self.log('==> %s' % resp)
        self.push(resp + '\r\n')

    def command_not_understood(self, command):
        self.respond("500 '%s': command not understood." % command)

    def command_not_authorized(self, command):
        self.respond(
            "530 You are not authorized to perform the '%s' command" % (
                command
            )
        )

    def make_xmit_channel(self):
        # In PASV mode, the connection may or may _not_ have been made
        # yet.  [although in most cases it is... FTP Explorer being
        # the only exception I've yet seen].  This gets somewhat confusing
        # because things may happen in any order...
        pa = self.passive_acceptor
        if pa:
            if pa.ready:
                # a connection has already been made.
                conn, addr = self.passive_acceptor.ready
                cdc = xmit_channel(self, addr)
                cdc.set_socket(conn)
                cdc.connected = 1
                self.passive_acceptor.close()
                self.passive_acceptor = None
            else:
                # we're still waiting for a connect to the PASV port.
                cdc = xmit_channel(self)
        else:
            # not in PASV mode.
            ip, port = self.client_addr
            cdc = xmit_channel(self, self.client_addr)
            cdc.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.bind_local_minus_one:
                cdc.bind(('', self.server.port - 1))
            try:
                cdc.connect((ip, port))
            except socket.error, why:
                self.respond("425 Can't build data connection")
        self.client_dc = cdc

    # pretty much the same as xmit, but only right on the verge of
    # being worth a merge.
    def make_recv_channel(self, fd):
        pa = self.passive_acceptor
        if pa:
            if pa.ready:
                # a connection has already been made.
                conn, addr = pa.ready
                cdc = recv_channel(self, addr, fd)
                cdc.set_socket(conn)
                cdc.connected = 1
                self.passive_acceptor.close()
                self.passive_acceptor = None
            else:
                # we're still waiting for a connect to the PASV port.
                cdc = recv_channel(self, None, fd)
        else:
            # not in PASV mode.
            ip, port = self.client_addr
            cdc = recv_channel(self, self.client_addr, fd)
            cdc.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                cdc.connect((ip, port))
            except socket.error, why:
                self.respond("425 Can't build data connection")
        self.client_dc = cdc

    type_map = {
        'a': 'ASCII',
        'i': 'Binary',
        'e': 'EBCDIC',
        'l': 'Binary'
    }

    type_mode_map = {
        'a': 't',
        'i': 'b',
        'e': 'b',
        'l': 'b'
    }

    # --------------------------------------------------
    # command methods
    # --------------------------------------------------

    def cmd_type(self, line):
        'specify data transfer type'
        # ascii, ebcdic, image, local <byte size>
        t = string.lower(line[1])
        # no support for EBCDIC
        # if t not in ['a','e','i','l']:
        if t not in ['a', 'i', 'l']:
            self.command_not_understood(string.join(line))
        elif t == 'l' and (len(line) > 2 and line[2] != '8'):
            self.respond('504 Byte size must be 8')
        else:
            self.current_mode = t
            self.respond('200 Type set to %s.' % self.type_map[t])

    def cmd_quit(self, line):
        'terminate session'
        self.respond('221 Goodbye.')
        self.close_when_done()

    def cmd_port(self, line):
        'specify data connection port'
        info = string.split(line[1], ',')
        ip = string.join(info[:4], '.')
        port = string.atoi(info[4]) * 256 + string.atoi(info[5])
        # how many data connections at a time?
        # I'm assuming one for now...
        # TODO: we should (optionally) verify that the
        # ip number belongs to the client.  [wu-ftpd does this?]
        self.client_addr = (ip, port)
        self.respond('200 PORT command successful.')

    def new_passive_acceptor(self):
        # ensure that only one of these exists at a time.
        if self.passive_acceptor is not None:
            self.passive_acceptor.close()
            self.passive_acceptor = None
        self.passive_acceptor = passive_acceptor(self)
        return self.passive_acceptor

    def cmd_pasv(self, line):
        'prepare for server-to-server transfer'
        pc = self.new_passive_acceptor()
        port = pc.addr[1]
        ip_addr = pc.control_channel.getsockname()[0]
        self.respond(
            '227 Entering Passive Mode (%s,%d,%d)' % (
                string.replace(ip_addr, '.', ','),
                port / 256,
                port % 256
            )
        )
        self.client_dc = None

    def cmd_nlst(self, line):
        'give name list of files in directory'
        # ncftp adds the -FC argument for the user-visible 'nlist'
        # command.  We could try to emulate ls flags, but not just yet.
        if '-FC' in line:
            line.remove('-FC')
        try:
            dir_list_producer = self.get_dir_list(line, 0)
        except os.error, why:
            self.respond('550 Could not list directory: %s' % why)
            return
        self.respond(
            '150 Opening %s mode data connection for file list' % (
                self.type_map[self.current_mode]
            )
        )
        self.make_xmit_channel()
        self.client_dc.push_with_producer(dir_list_producer)
        self.client_dc.close_when_done()

    def cmd_list(self, line):
        'give a list of files in a directory'
        try:
            dir_list_producer = self.get_dir_list(line, 1)
        except os.error, why:
            self.respond('550 Could not list directory: %s' % why)
            return
        self.respond(
            '150 Opening %s mode data connection for file list' % (
                self.type_map[self.current_mode]
            )
        )
        self.make_xmit_channel()
        self.client_dc.push_with_producer(dir_list_producer)
        self.client_dc.close_when_done()

    def cmd_cwd(self, line):
        'change working directory'
        if self.cwd(line):
            self.respond('250 CWD command successful.')
        else:
            self.respond('550 No such directory.')

    def cmd_cdup(self, line):
        'change to parent of current working directory'
        if self.cdup(line):
            self.respond('250 CDUP command successful.')
        else:
            self.respond('550 Permission denied.')

    def cmd_pwd(self, line):
        'print the current working directory'
        self.respond(
            '257 "%s" is the current directory.' % (
                self.filesystem.current_directory()
            )
        )

    def cmd_rnfr(self, line):
        'get filename to change'
        if self.rnfr(line):
            self.respond('250 RNFR command successful.')
        else:
            self.respond('550 File not found.')

    def cmd_rnto(self, line):
        'get filename change to'
        if self.rnto(line):
            self.respond('250 RNTO command successful.')
        else:
            self.respond('550 File not found.')

    # modification time
    # example output:
    # 213 19960301204320
    def cmd_mdtm(self, line):
        'show last modification time of file'
        filename = line[1]
        if not self.filesystem.isfile(filename):
            self.respond('550 "%s" is not a file' % filename)
        else:
            mtime = time.gmtime(self.filesystem.stat(filename)[stat.ST_MTIME])
            self.respond(
                '213 %4d%02d%02d%02d%02d%02d' % (
                    mtime[0],
                    mtime[1],
                    mtime[2],
                    mtime[3],
                    mtime[4],
                    mtime[5]
                )
            )

    def cmd_noop(self, line):
        'do nothing'
        self.respond('200 NOOP command successful.')

    def cmd_size(self, line):
        'return size of file'
        filename = line[1]
        if not self.filesystem.isfile(filename):
            self.respond('550 "%s" is not a file' % filename)
        else:
            self.respond(
                '213 %d' % (self.filesystem.stat(filename)[stat.ST_SIZE])
            )

    def cmd_retr(self, line):
        'retrieve a file'
        if len(line) < 2:
            self.command_not_understood(string.join(line))
        else:
            file = line[1]
            if not self.filesystem.isfile(file):
                logg.info('checking %s', file)
                self.respond('550 No such file')
            else:
                try:
                    # FIXME: for some reason, 'rt' isn't working on win95
                    mode = 'r' + self.type_mode_map[self.current_mode]
                    fd = self.open(file, mode)
                except IOError, why:
                    self.respond('553 could not open file for reading: %s' % (repr(why)))
                    return
                self.respond(
                    "150 Opening %s mode data connection for file '%s'" % (
                        self.type_map[self.current_mode],
                        file
                    )
                )
                self.make_xmit_channel()

                if self.restart_position:
                    # try to position the file as requested, but
                    # give up silently on failure (the 'file object'
                    # may not support seek())
                    try:
                        fd.seek(self.restart_position)
                    except:
                        pass
                    self.restart_position = 0

                self.client_dc.push_with_producer(
                    file_producer(fd)
                )
                self.client_dc.close_when_done()

    def cmd_stor(self, line, mode='wb'):
        'store a file'
        if len(line) < 2:
            self.command_not_understood(string.join(line))
        else:
            if self.restart_position:
                restart_position = 0
                self.respond('553 restart on STOR not yet supported')
                return
            file = line[1]
            # todo: handle that type flag
            try:
                fd = self.open(file, mode)
            except IOError, why:
                self.respond('553 could not open file for writing: %s' % (repr(why)))
                return
            self.respond(
                '150 Opening %s connection for %s' % (
                    self.type_map[self.current_mode],
                    file
                )
            )
            self.make_recv_channel(fd)

    def cmd_abor(self, line):
        'abort operation'
        if self.client_dc:
            self.client_dc.close()
        self.respond('226 ABOR command successful.')

    def cmd_appe(self, line):
        'append to a file'
        return self.cmd_stor(line, 'ab')

    def cmd_dele(self, line):
        if len(line) != 2:
            self.command_not_understood(string.join(line))
        else:
            file = line[1]
            if self.filesystem.isfile(file):
                try:
                    self.filesystem.unlink(file)
                    self.respond('250 DELE command successful.')
                except:
                    print exception_string()
                    self.respond('550 error deleting file.')
            else:
                self.respond('550 %s: No such file.' % file)

    def cmd_mkd(self, line):
        if len(line) != 2:
            self.command_not_understood(string.join(line))
        else:
            path = line[1]
            try:
                self.filesystem.mkdir(path)
                self.respond('257 MKD command successful.')
            except:
                print exception_string()
                self.respond('550 error creating directory.')

    def cmd_rmd(self, line):
        if len(line) != 2:
            self.command_not_understood(string.join(line))
        else:
            path = line[1]
            try:
                self.filesystem.rmdir(path)
                self.respond('250 RMD command successful.')
            except:
                print exception_string()
                self.respond('550 error removing directory.')

    def cmd_user(self, line):
        'specify user name'
        if len(line) > 1:
            self.user = line[1]
            self.respond('331 Password required.')
        else:
            self.command_not_understood(string.join(line))

    def cmd_pass(self, line):
        'specify password'
        if len(line) < 2:
            pw = ''
        else:
            pw = line[1]
        result, message, fs = self.server.authorizer.authorize(self, self.user, pw)
        if result:
            self.respond('230 %s' % message)
            self.filesystem = fs
            self.authorized = 1
        else:
            self.respond('530 %s' % message)

    def cmd_rest(self, line):
        'restart incomplete transfer'
        try:
            pos = string.atoi(line[1])
        except ValueError:
            self.command_not_understood(string.join(line))
        self.restart_position = pos
        self.respond(
            '350 Restarting at %d. Send STORE or RETRIEVE to initiate transfer.' % pos
        )

    def cmd_stru(self, line):
        'obsolete - set file transfer structure'
        if line[1] in 'fF':
            # f == 'file'
            self.respond('200 STRU F Ok')
        else:
            self.respond('504 Unimplemented STRU type')

    def cmd_mode(self, line):
        'obsolete - set file transfer mode'
        if line[1] in 'sS':
            # f == 'file'
            self.respond('200 MODE S Ok')
        else:
            self.respond('502 Unimplemented MODE type')

# The stat command has two personalities.  Normally it returns status
# information about the current connection.  But if given an argument,
# it is equivalent to the LIST command, with the data sent over the
# control connection.  Strange.  But wuftpd, ftpd, and nt's ftp server
# all support it.
#
# def cmd_stat (self, line):
##              'return status of server'
# pass

    def cmd_syst(self, line):
        'show operating system type of server system'
        # Replying to this command is of questionable utility, because
        # this server does not behave in a predictable way w.r.t. the
        # output of the LIST command.  We emulate Unix ls output, but
        # on win32 the pathname can contain drive information at the front
        # Currently, the combination of ensuring that os.sep == '/'
        # and removing the leading slash when necessary seems to work.
        # [cd'ing to another drive also works]
        #
        # This is how wuftpd responds, and is probably
        # the most expected.  The main purpose of this reply is so that
        # the client knows to expect Unix ls-style LIST output.
        self.respond('215 UNIX Type: L8')
        # one disadvantage to this is that some client programs
        # assume they can pass args to /bin/ls.
        # a few typical responses:
        # 215 UNIX Type: L8 (wuftpd)
        # 215 Windows_NT version 3.51
        # 215 VMS MultiNet V3.3
        # 500 'SYST': command not understood. (SVR4)

    def cmd_help(self, line):
        'give help information'
        # find all the methods that match 'cmd_xxxx',
        # use their docstrings for the help response.
        attrs = dir(self.__class__)
        help_lines = []
        for attr in attrs:
            if attr[:4] == 'cmd_':
                x = getattr(self, attr)
                if type(x) == type(self.cmd_help):
                    if x.__doc__:
                        help_lines.append('\t%s\t%s' % (attr[4:], x.__doc__))
        if help_lines:
            self.push('214-The following commands are recognized\r\n')
            self.push_with_producer(lines_producer(help_lines))
            self.push('214\r\n')
        else:
            self.push('214-\r\n\tHelp Unavailable\r\n214\r\n')


class ftp_server (asyncore.dispatcher):
    # override this to spawn a different FTP channel class.
    ftp_channel_class = ftp_channel

    SERVER_IDENT = 'FTP Server (V%s)' % VERSION

    def __init__(
            self,
            authorizer,
            hostname=None,
            ip='',
            port=21,
    ):
        self.ip = ip
        self.port = port
        self.authorizer = authorizer

        if hostname is None:
            self.hostname = socket.gethostname()
        else:
            self.hostname = hostname

        # statistics
        self.total_sessions = counter()
        self.closed_sessions = counter()
        self.total_files_out = counter()
        self.total_files_in = counter()
        self.total_bytes_out = counter()
        self.total_bytes_in = counter()
        self.total_exceptions = counter()
        #
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        self.set_reuse_addr()
        self.bind((self.ip, self.port))
        self.listen(5)

        logftp.info('FTP server started, Port: %d\n\tAuthorizer: %s, Hostname: %s\n',
                    self.port,
                    repr(self.authorizer),
                    self.hostname)

    def writable(self):
        return 0

    def handle_read(self):
        pass

    def handle_connect(self):
        pass

    def handle_accept(self):
        conn, addr = self.accept()
        self.total_sessions.increment()
        logftp.debug('Incoming connection from %s:%d', addr[0], addr[1])
        self.ftp_channel_class(self, conn, addr)

    # return a producer describing the state of the server
    def status(self):

        def nice_bytes(n):
            return string.join(english_bytes(n))

        return lines_producer(
            ['<h2>%s</h2>' % self.SERVER_IDENT,
             '<br>Listening on <b>Host:</b> %s' % self.hostname,
             '<b>Port:</b> %d' % self.port,
             '<br>Sessions',
             '<b>Total:</b> %s' % self.total_sessions,
             '<b>Current:</b> %d' % (self.total_sessions.as_long() - self.closed_sessions.as_long()),
             '<br>Files',
             '<b>Sent:</b> %s' % self.total_files_out,
             '<b>Received:</b> %s' % self.total_files_in,
             '<br>Bytes',
             '<b>Sent:</b> %s' % nice_bytes(self.total_bytes_out.as_long()),
             '<b>Received:</b> %s' % nice_bytes(self.total_bytes_in.as_long()),
             '<br>Exceptions: %s' % self.total_exceptions,
             ]
        )

# ======================================================================
#                                                Data Channel Classes
# ======================================================================

# This socket accepts a data connection, used when the server has been
# placed in passive mode.  Although the RFC implies that we ought to
# be able to use the same acceptor over and over again, this presents
# a problem: how do we shut it off, so that we are accepting
# connections only when we expect them?  [we can't]
#
# wuftpd, and probably all the other servers, solve this by allowing
# only one connection to hit this acceptor.  They then close it.  Any
# subsequent data-connection command will then try for the default
# port on the client side [which is of course never there].  So the
# 'always-send-PORT/PASV' behavior seems required.
#
# Another note: wuftpd will also be listening on the channel as soon
# as the PASV command is sent.  It does not wait for a data command
# first.

# --- we need to queue up a particular behavior:
#  1) xmit : queue up producer[s]
#  2) recv : the file object
#
# It would be nice if we could make both channels the same.  Hmmm..
#


class passive_acceptor (asyncore.dispatcher):
    ready = None

    def __init__(self, control_channel):
        # connect_fun (conn, addr)
        asyncore.dispatcher.__init__(self)
        self.control_channel = control_channel
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind to an address on the interface that the
        # control connection is coming from.
        self.bind((
            self.control_channel.getsockname()[0],
            0
        ))
        self.addr = self.getsockname()
        self.listen(1)

#       def __del__ (self):
#               print 'passive_acceptor.__del__()'

    def log(self, *ignore):
        pass

    def handle_accept(self):
        conn, addr = self.accept()
        dc = self.control_channel.client_dc
        if dc is not None:
            dc.set_socket(conn)
            dc.addr = addr
            dc.connected = 1
            self.control_channel.passive_acceptor = None
        else:
            self.ready = conn, addr
        self.close()


class xmit_channel (async_chat):

    # for an ethernet, you want this to be fairly large, in fact, it
    # _must_ be large for performance comparable to an ftpd.  [64k] we
    # ought to investigate automatically-sized buffers...

    ac_out_buffer_size = 16384
    bytes_out = 0

    def __init__(self, channel, client_addr=None):
        self.channel = channel
        self.client_addr = client_addr
        async_chat.__init__(self)

#       def __del__ (self):
#               print 'xmit_channel.__del__()'

    def log(self, *args):
        pass

    def readable(self):
        return not self.connected

    def writable(self):
        return 1

    def send(self, data):
        result = async_chat.send(self, data)
        self.bytes_out = self.bytes_out + result
        return result

    def handle_error(self):
        # usually this is to catch an unexpected disconnect.
        logg.error('unexpected disconnect on data xmit channel')
        try:
            self.close()
        except:
            pass

    # TODO: there's a better way to do this.  we need to be able to
    # put 'events' in the producer fifo.  to do this cleanly we need
    # to reposition the 'producer' fifo as an 'event' fifo.

    def close(self):
        c = self.channel
        s = c.server
        c.client_dc = None
        s.total_files_out.increment()
        s.total_bytes_out.increment(self.bytes_out)
        if not len(self.producer_fifo):
            c.respond('226 Transfer complete')
        elif not c.closed:
            c.respond('426 Connection closed; transfer aborted')
        del c
        del s
        del self.channel
        try:
            async_chat.close(self)
        except:
            pass


class recv_channel (asyncore.dispatcher):

    def __init__(self, channel, client_addr, fd):
        self.channel = channel
        self.client_addr = client_addr
        self.fd = fd
        asyncore.dispatcher.__init__(self)
        self.bytes_in = counter()

    def log(self, *ignore):
        pass

    def handle_connect(self):
        pass

    def writable(self):
        return 0

    def recv(*args):
        result = apply(asyncore.dispatcher.recv, args)
        self = args[0]
        self.bytes_in.increment(len(result))
        return result

    buffer_size = 8192

    def handle_read(self):
        block = self.recv(self.buffer_size)
        if block:
            try:
                self.fd.write(block)
            except IOError:
                logg.info('got exception writing block...', exc_info=1)

    def handle_close(self):
        s = self.channel.server
        s.total_files_in.increment()
        s.total_bytes_in.increment(self.bytes_in.as_long())
        self.fd.close()
        self.channel.respond('226 Transfer complete.')
        self.close()


import getopt
import re
import sys
import asyncore
import os
import random
import importlib
import time
import thread
import stat
import urllib
import traceback
import zipfile

HTTP_CONTINUE = 100
HTTP_SWITCHING_PROTOCOLS = 101
HTTP_PROCESSING = 102
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NON_AUTHORITATIVE = 203
HTTP_NO_CONTENT = 204
HTTP_RESET_CONTENT = 205
HTTP_PARTIAL_CONTENT = 206
HTTP_MULTI_STATUS = 207
HTTP_MULTIPLE_CHOICES = 300
HTTP_MOVED_PERMANENTLY = 301
HTTP_MOVED_TEMPORARILY = 302
HTTP_SEE_OTHER = 303
HTTP_NOT_MODIFIED = 304
HTTP_USE_PROXY = 305
HTTP_TEMPORARY_REDIRECT = 307
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_PAYMENT_REQUIRED = 402
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_NOT_ACCEPTABLE = 406
HTTP_PROXY_AUTHENTICATION_REQUIRED = 407
HTTP_REQUEST_TIME_OUT = 408
HTTP_CONFLICT = 409
HTTP_GONE = 410
HTTP_LENGTH_REQUIRED = 411
HTTP_PRECONDITION_FAILED = 412
HTTP_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_REQUEST_URI_TOO_LARGE = 414
HTTP_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_RANGE_NOT_SATISFIABLE = 416
HTTP_EXPECTATION_FAILED = 417
HTTP_IM_A_TEAPOT = 418
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_LOCKED = 423
HTTP_FAILED_DEPENDENCY = 424
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_NOT_IMPLEMENTED = 501
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIME_OUT = 504
HTTP_VERSION_NOT_SUPPORTED = 505
HTTP_VARIANT_ALSO_VARIES = 506
HTTP_INSUFFICIENT_STORAGE = 507
HTTP_NOT_EXTENDED = 510

GLOBAL_TEMP_DIR = "/tmp/"
GLOBAL_ROOT_DIR = "no-root-dir-set"
verbose = 1
multithreading_enabled = 0
number_of_threads = 32


def qualify_path(p):
    if p[-1] != '/':
        return p + "/"
    return p


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


ftphandlers = []
contexts = []

global_modules = {}


def _load_module(filename):
    global global_modules
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

    dir = os.path.dirname(filename)
    path = dir.replace("/", ".")

    # strip tailing/leading dots
    while len(path) and path[0] == '.':
        path = path[1:]
    while len(path) and path[-1] != '.':
        path = path + "."

    module2 = (path + module)
    logg.debug("Loading module %s", module2)

    m = importlib.import_module(module2)
    global_modules[filename] = m
    return m

system_modules = sys.modules.copy()
stdlib, x = os.path.split(os.__file__)


def _purge_all_modules():
    for m, mod in sys.modules.items():
        if m not in system_modules:
            if hasattr(mod, "__file__"):
                f = mod.__file__
                path, x = os.path.split(f)
                if not path.startswith(stdlib):
                    del sys.modules[m]


class WebContext:

    def __init__(self, name, root=None):
        self.name = name
        self.files = []
        self.startupfile = None
        if root:
            self.root = qualify_path(root)
        self.pattern_to_function = OrderedDict()
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
        logg.info("  executing startupfile")
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
                    return req.error(status)
            return req.done()

        for pattern, call in self.pattern_to_function.items():
            if pattern.match(path):
                function, desc = call
                if verbose:
                    logg.debug("Request %s matches (%s)", path, desc)
                return lambda req: call_and_close(function, req)

        # no pattern matched, use catchall handler if present
        if self.catchall_handler:
            return partial(call_and_close, self.catchall_handler.f)

        return None


class WSGIHandler(object):

    def __init__(self, app, context_name, path):
        self.app = app
        self.context_name = context_name
        self.path = path

    def start_response(self, status, response_headers, exc_info=None):
        self.request.reply_headers.update(dict(response_headers))
        self.status = status
        return self.request.write

    def make_environ(self):
        from StringIO import StringIO
        request = self.request
        query = request.query[1:] if request.query is not None else ""
        request_body = StringIO(request._data) if hasattr(request, "_data") else StringIO()

        # SERVER_NAME is unknown, we can only use localhost...
        environ = {
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": self.context_name,
            "PATH_INFO": wsgi_encoding_dance(self.path),
            "QUERY_STRING": wsgi_encoding_dance(query),
            "CONTENT_TYPE": request.request_headers.get("content-type", ""),
            "CONTENT_LENGTH": request.request_headers.get("content-length", ""),
            'REMOTE_ADDR': request.channel.addr[0],
            'REMOTE_PORT': request.channel.addr[1],
            "SERVER_NAME": "localhost",
            "SERVER_PORT": request.channel.server.port,
            "SERVER_PROTOCOL": "HTTP/" + request.version,
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": request_body,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": multithreading_enabled,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False
        }

        for key, value in request.request_headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value

        return environ

    def __call__(self, request):


        self.request = request
        environ = self.make_environ()

        try:
            content = self.app(environ, self.start_response)
        except:
            logg.exception("exception in WSGI app:")
            request.error(500, "WSGI app failed")
            return

        for elem in content:
            request.write(elem)

        spl = self.status.split(" ", 1)
        status_code = int(spl[0])
        reason = spl[1] if len(spl) == 2 else None

        request.setStatus(status_code)
        request.done()


class WSGIContext(object):

    def __init__(self, name, app):
        self.name = name
        self.app = app

    def match(self, path):
        """we don't really "match" here, just for compatibility with Athana's WebContext"""
        return WSGIHandler(self.app, self.name, path)


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
        return request.error(404, "File " + request.path + " not found")

    def addRoot(self, dir):
        if not os.path.isabs(dir):
            dir = qualify_path(dir)
            while dir.startswith("./"):
                dir = dir[2:]
            dir = os.path.join(GLOBAL_ROOT_DIR, dir)

        if zipfile.is_zipfile(dir[:-1]) and dir.lower().endswith("zip/"):
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
        try:
            c = eval("m." + ftpclass)
            if c is None:
                raise
            ftphandlers += [c]
        except:
            logg.error("Error in FTP Handler:", exc_info=1)
            raise AthanaException("No such function " + ftpclass + " in file " + self.filename)

    def getFileName(self):
        return self.context.root + self.filename


class WebHandler:

    def __init__(self, file, function):
        self.file = file
        if isinstance(function, str):
            self.function = function
            m = file.m
            try:
                self.f = getattr(m, function)
            except:
                logg.error("Error in Handler", exc_info=1)
                raise AthanaException("No such function " + function + " in file " + self.file.filename)
        else:
            self.f = function
            self.function = function.func_name

    def addPattern(self, pattern):
        p = WebPattern(self, pattern)
        desc = "pattern %s, file %s, function %s" % (pattern, self.file.filename, self.function)
        desc2 = "file %s, function %s" % (self.file.filename, self.function)
        self.file.context.pattern_to_function[p.getPattern()] = (self.f, desc)
        return p


class WebPattern:

    def __init__(self, handler, pattern):
        self.handler = handler
        self.pattern = pattern
        if not pattern.endswith('$'):
            pattern = pattern + "$"
        self.compiled = re.compile(pattern)

    def getPattern(self):
        return self.compiled

    def getPatternString(self):
        return self.pattern


def read_ini_file(filename):
    global GLOBAL_TEMP_DIR, GLOBAL_ROOT_DIR, number_of_threads, multithreading_enabled, contexts
    lineno = 0
    fi = open(filename, "rb")
    file = None
    function = None
    context = None
    GLOBAL_ROOT_DIR = '/'
    for line in fi.readlines():
        lineno = lineno + 1
        hashpos = line.find("#")
        if hashpos >= 0:
            line = line[0:hashpos]
        line = line.strip()

        if line == "":
            continue  # skip empty line

        equals = line.find(":")
        if equals < 0:
            continue
        key = line[0:equals].strip()
        value = line[equals + 1:].strip()
        if key == "tempdir":
            GLOBAL_TEMP_DIR = qualify_path(value)
        elif key == "threads":
            number_of_threads = int(value)
            multithreading_enabled = 1
        elif key == "base":
            GLOBAL_ROOT_DIR = qualify_path(value)
            sys.path += [GLOBAL_ROOT_DIR]
        elif key == "filestore":
            if len(value) and value[0] != '/':
                value = "/" + value
            filestore = FileStore(value)
            contexts += [filestore]
            context = None
        elif key == "context":
            if len(value) and value[0] != '/':
                value = "/" + value
            contextname = value
            context = WebContext(contextname)
            contexts += [context]
            filestore = None
        elif key == "startupfile":
            if context is not None:
                context.setStartupFile(value)
            else:
                raise AthanaException("Error: startupfile must be below a context")
        elif key == "root":
            if value.startswith('/'):
                value = value[1:]
            if context:
                context.setRoot(value)
            if filestore:
                filestore.addRoot(value)
        elif key == "file":
            filename = value
            file = context.addFile(filename)
        elif key == "ftphandler":
            file.addFTPHandler(value)
        elif key == "handler":
            function = value
            handler = file.addHandler(function)
        elif key == "pattern":
            handler.addPattern(value)
        else:
            raise AthanaException("Syntax error in line " + ustr(lineno) + " of file " + filename + ":\n" + line)
    fi.close()
    return context


def headers_to_map(mylist):
    headers = {}
    for h in mylist:
        try:
            i = h.index(':')
        except:
            i = -1
        if i >= 0:
            key = h[0:i].lower()
            value = h[i + 1:]
            if len(value) > 0 and value[0] == ' ':
                value = value[1:]
            headers[key] = value
        else:
            if len(h.strip()) > 0:
                logg.error("invalid header: %s", h)
    return headers


class AthanaFile:

    def __init__(self, fieldname, param_list, filename, content_type):
        self.fieldname = fieldname
        self.param_list = param_list
        self.filename = filename
        self.content_type = content_type
        self.tempname = GLOBAL_TEMP_DIR + ustr(int(random.random() * 999999)) + os.path.splitext(filename)[1]
        self.filesize = 0
        self.fi = open(self.tempname, "wb")

    def adddata(self, data):
        self.filesize += len(data)
        self.fi.write(data)

    def close(self):
        self.fi.close()
        # only append file to parameters if it contains some data
        if self.filename or self.filesize:
            self.param_list.append((self.fieldname, self))
        del self.fieldname
        del self.param_list
        del self.fi
        logg.debug("closed file %s (%s)", self.filename, self.tempname)

    def __str__(self):
        return "file %s (%s), %d bytes, content-type: %s" % (self.filename, self.tempname, self.filesize, self.content_type)


class AthanaField:

    def __init__(self, fieldname, param_list):
        self.fieldname = fieldname
        self.data = ""
        self.param_list = param_list

    def adddata(self, data):
        self.data += data

    def close(self):
        self.param_list.append((self.fieldname, self.data))
        del self.data
        del self.param_list


class simple_input_collector:

    def __init__(self, handler, request, length):
        self.request = request
        self.length = length
        self.handler = handler
        request.channel.set_terminator(length)
        self.data = ""

    def collect_incoming_data(self, data):
        self.data += data

    def found_terminator(self):
        self.request.channel.set_terminator('\r\n\r\n')
        self.request.collector = None
        d = self.data
        del self.data
        r = self.request
        del self.request
        r._data = d
        pairs = []
        data = d.split('&')
        for e in data:
            if '=' in e:
                i = e.index('=')
                key, value = e[:i], e[i + 1:]
                key = urllib.unquote_plus(key)
                pairs.append((key, urllib.unquote_plus(value)))
            else:
                if len(e.strip()) > 0:
                    logg.warn("corrupt parameter: %s", e.encode("string-escape"))
        self.handler.continue_request(r, pairs)

class upload_input_collector:


    def __init__(self, handler, request, length, boundary):
        self.request = request
        self.length = length
        self.handler = handler
        self.boundary = boundary
        request.channel.set_terminator(length)
        self.data = ""
        self._all_data = array('c', '')
        self.pos = 0
        self.start_marker = "--" + boundary + "\r\n"
        self.end_marker = "--" + boundary + "--"
        self.prefix = "--" + boundary
        self.marker = "\r\n--" + boundary
        self.header_end_marker = "\r\n\r\n"
        self.current_file = None
        self.boundary = boundary
        self.file = None
        self.form = []
        self.files = []
        self.tempfiles = request.tempfiles = []

    def parse_semicolon_parameters(self, params):
        params = params.split("; ")
        parmap = {}
        for a in params:
            if '=' in a:
                i = a.index('=')
                key, value = a[:i], a[i + 1:]
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                parmap[key] = value
        return parmap

    def startFile(self, headers):
        fieldname = None
        filename = None
        if self.file is not None:
            raise AthanaException("Illegal state")
        if "content-disposition" in headers:
            cd = headers["content-disposition"]
            l = self.parse_semicolon_parameters(cd)
            if "name" in l:
                fieldname = l["name"]
            if "filename" in l:
                filename = l["filename"]
        if "content-type" in headers:
            content_type = headers["content-type"]
            self.file = AthanaFile(fieldname, self.form, filename, content_type)
            logg.debug("opened file %s (%s)", filename, self.file.tempname)
            self.files.append(self.file)
            self.tempfiles.append(self.file.tempname)
        else:
            self.file = AthanaField(fieldname, self.form)

    def split_headers(self, string):
        return string.split("\r\n")

    def collect_incoming_data(self, newdata):
        self.pos += len(newdata)
        self.data += newdata
        self._all_data += array('c', newdata)

        while len(self.data) > 0:
            if self.data.startswith(self.end_marker):
                self.data = self.data[len(self.end_marker):]
                self.data = self.data.lstrip()
                if self.file is not None:
                    self.file.close()
                    self.file = None
                return
            elif self.data.startswith(self.start_marker):
                try:
                    i = self.data.index(self.header_end_marker, len(self.start_marker))
                except:
                    i = -1
                if i >= 0:
                    headerstr = self.data[len(self.start_marker):i + 2]
                    headers = headers_to_map(self.split_headers(headerstr))
                    self.startFile(headers)
                    self.data = self.data[i + len(self.header_end_marker):]
                else:
                    return  # wait for more data (inside headers)
            elif self.data.startswith(self.prefix):
                return
            else:
                try:
                    bindex = self.data.index(self.marker)
                    self.file.adddata(self.data[0:bindex])
                    self.file.close()
                    self.file = None
                    self.data = self.data[bindex + 2:]  # cut to position after \r\n
                except ValueError:  # not found
                    if(len(self.data) <= len(self.marker)):
                        return  # wait for more data before we make a decision or pass through data
                    else:
                        self.file.adddata(self.data[0:-len(self.marker)])
                        self.data = self.data[-len(self.marker):]

    def found_terminator(self):
        if len(self.data) > 0:  # and self.file is not None:
            if self.file is not None:
                self.file.close()
                self.file = None
            raise AthanaException("Unfinished/malformed multipart request")
        if self.file is not None:
            self.file.close()
            self.file = None

        self.request.collector = None
        self.request.channel.set_terminator('\r\n\r\n')
        d = self.data
        del self.data
        r = self.request
        r._data = self._all_data.tostring()
        del self.request
        self.handler.continue_request(r, self.form)


# XXX: hack for better testing, do not use this in production...
USE_PERSISTENT_SESSIONS = False


try:
    import redis_collections
except ImportError:
    pass
else:
    class RedisSession(redis_collections.Dict):

        def __init__(self, key):
            super(RedisSession, self).__init__(key=key)

        @property
        def id(self):
            return self.key

        def use(self):
            pass


class Session(dict):

    def __init__(self, id):
        self.id = id

    def use(self):
        self.lastuse = time.time()


def exception_string():
    s = "Exception " + ustr(sys.exc_info()[0])
    info = sys.exc_info()[1]
    if info:
        s += " " + ustr(info)
    s += "\n"
    for l in traceback.extract_tb(sys.exc_info()[2]):
        s += "  File \"%s\", line %d, in %s\n" % (l[0], l[1], l[2])
    s += "    %s\n" % l[3]
    return s

BASENAME = re.compile("([^/]*/)*([^/.]*)(.py)?")
MULTIPART = re.compile('multipart/form-data.*boundary=([^ ]*)', re.IGNORECASE)
SESSION_PATTERN = re.compile("^;[a-z0-9]{6}-[a-z0-9]{6}-[a-z0-9]{6}$")
SESSION_PATTERN2 = re.compile("[a-z0-9]{6}-[a-z0-9]{6}-[a-z0-9]{6}")

SESSION_COOKIES_LIVE_SECS = 3600 * 2  # unused sessions may be valid for 2 hours


# COMPAT: flask style
def filter_out_files(param_list):
    form = []
    files = []
    for kv in param_list:
        if isinstance(kv[1], AthanaFile):
            files.append(kv)
        else:
            form.append(kv)
    return form, files


def make_param_dict_utf8_values(param_list):
    def decode(k):
        try:
            return unicode(k, encoding="utf8")
        except UnicodeDecodeError as e:
            logg.warn("tried to decode non-UTF8 string: %s", k.encode("string-escape"))
            raise

    return ImmutableMultiDict([(decode(k), decode(v)) for k, v in param_list])
# /COMPAT

# COMPAT: before / after request handlers and request / app context handling
_request_started_handlers = []
_request_finished_handlers = []

app = None


def call_handler_func(handler, handler_func, request):

    # WSGI passthrough. WSGIHandler takes care of the rest
    if isinstance(handler_func, WSGIHandler):
        handler_func(request)

    elif app:
        with app.request_context(request, request.session):
            handler.callhandler(handler_func, request)
    else:
        handler.callhandler(handler_func, request)
# /COMPAT


class AthanaHandler:

    def __init__(self):
        self.sessions = {}
        self.queue = []
        self.queuelock = thread.allocate_lock()

    def match(self, request):
        path, params, query, fragment = request.split_uri()
        return 1

    def handle_request(self, request):
        headers = headers_to_map(request.header)
        request.request_headers = headers

        size = headers.get("content-length", None)

        if size and size != '0':
            size = int(size)
            ctype = headers.get("content-type", None)
            b = MULTIPART.match(ctype) if ctype else None
            if b is not None:
                request.type = "MULTIPART"
                boundary = b.group(1)
                request.collector = upload_input_collector(self, request, size, boundary)
            else:
                request.type = "POST"
                request.collector = simple_input_collector(self, request, size)
        else:
            request.type = "GET"
            self.continue_request(request, form=[])

    def create_session_id(self):
        pid = abs((ustr(random.random())).__hash__())
        now = abs((ustr(time.time())).__hash__())
        rand = abs((ustr(random.random())).__hash__())
        x = "abcdefghijklmnopqrstuvwxyz0123456789"
        result = ""
        for a in range(0, 6):
            result += x[pid % 36]
            pid = pid / 36
        result += "-"
        for a in range(0, 6):
            result += x[now % 36]
            now = now / 36
        result += "-"
        for a in range(0, 6):
            result += x[rand % 36]
            rand = rand / 36
        return result

    # COMPAT: new param style like flask
    @staticmethod
    def parse_query(query):
        if query[0] == '?':
            query = query[1:]
        query = query.split('&')
        args = []
        for e in query:
            try:
                i = e.index('=')
                key, value = e[:i], e[i + 1:]
            except ValueError:
                key = e
                value = ""
            key = urllib.unquote_plus(key)
            args.append((key, urllib.unquote_plus(value)))
        return args
    # / COMPAT

    def continue_request(self, request, form):

        path, params, query, fragment = request.split_uri()

        ip = request.request_headers.get("x-forwarded-for", None)
        if ip is None:
            try:
                ip = request.channel.addr[0]
            except:
                pass
        if ip:
            request.channel.addr = (ip, request.channel.addr[1])

        request.log()

        # COMPAT: new param style like flask
        if query is not None:
            args = AthanaHandler.parse_query(query)
        else:
            args = []
        # /COMPAT

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
                    logg.warn("corrupt cookie value: %s", a.encode("string-escape"))

        request.Cookies = cookies

        sessionid = None
                
        if "PSESSION" in cookies:
            sessionid = cookies["PSESSION"]

        if USE_PERSISTENT_SESSIONS:
            if sessionid is None:
                sessionid = self.create_session_id()
                logg.debug("Creating new session %s", sessionid)

            session = RedisSession(sessionid)
        else:
            if sessionid is not None:
                if sessionid in self.sessions:
                    session = self.sessions[sessionid]
                    session.use()
                else:
                    session = Session(sessionid)
                    self.sessions[sessionid] = session
            else:
                sessionid = self.create_session_id()
                logg.debug("Creating new session %s", sessionid)
                session = Session(sessionid)
                self.sessions[sessionid] = session

        request['Content-Type'] = 'text/html; encoding=utf-8; charset=utf-8'

        maxlen = -1
        context = None
        global contexts
        for c in contexts:
            if path.startswith(c.name) and len(c.name) > maxlen:
                context = c
                maxlen = len(context.name)
                
        if context is None:
            request.error(404)
            return

        fullpath = path
        path = path[len(context.name):]
        if len(path) == 0 or path[0] != '/':
            path = "/" + path

        request.session = session
        request.sessionid = sessionid
        request.context = context
        request.path = path
        request.fullpath = fullpath
        request.paramstring = params
        request.query = query
        request.fragment = fragment
        # COMPAT: new param style like flask
        # we don't need this for WSGI, args / form parsing is done by the WSGI app
        if not isinstance(context, WSGIContext):
            form, files = filter_out_files(form)
            try:
                request.args = make_param_dict_utf8_values(args)
                request.form = make_param_dict_utf8_values(form)
            except UnicodeDecodeError:
                return request.error(400)

            request.files = ImmutableMultiDict(files)
            request.make_legacy_params_dict()
        # /COMPAT
        request.request = request
        request.ip = ip
        request.uri = request.uri.replace(context.name, "/")
        request._split_uri = None


        request.channel.current_request = None

        if path == "/threadstatus":
            return thread_status(request)
        if path == "/profilingstatus":
            return profiling_status(request)

        function = context.match(path)

        if function is not None:
            if not multithreading_enabled:
                call_handler_func(self, function, request)
            else:
                self.queuelock.acquire()
                self.queue += [(function, request)]
                self.queuelock.release()
            return
        else:
            logg.debug("Request %s matches no pattern (context: %s)", request.path, context.name)
            return request.error(404, "File %s not found" % request.path)

    def callhandler(self, handler_func, req):
        for handler in _request_started_handlers:
            handler(req)

        s = None
        try:
            status = handler_func(req)
        except Exception as e:
            # XXX: this shouldn't be in Athana, most of it is mediaTUM-specific...
            # TODO: add some kind of exception handler system for Athana
            import core.config as config
            request = req.request
            if config.get('host.type') != 'testing':
                from utils.log import make_xid_and_errormsg_hash, extra_log_info_from_req
                from core.translation import translate
                from core import db

                # Roll back if the error was caused by a database problem. 
                # DB requests in this error handler will fail until rollback is called, so let's do it here.
                db.session.rollback()
                
                xid, hashed_errormsg, hashed_tb = make_xid_and_errormsg_hash()

                mail_to_address = config.get('email.support')
                if not mail_to_address:
                    logg.warn("no support mail address configured, consider setting it with `email.support`", trace=False)

                log_extra = {"xid": xid,
                             "error_hash": hashed_errormsg,
                             "trace_hash": hashed_tb}
                
                log_extra["req"] = extra_log_info_from_req(req)

                logg.exception(u"exception (xid=%s) while handling request %s %s, %s",
                               xid, req.method, req.path, dict(req.args), extra=log_extra)

                if mail_to_address:
                    msg = translate("core_snipped_internal_server_error_with_mail", request=req).replace('${email}', mail_to_address)
                else:
                    msg = translate("core_snipped_internal_server_error_without_mail", request=req)
                s = msg.replace('${XID}', xid)

                req.reply_headers["X-XID"] = xid
                    
                return request.error(500, s.encode("utf8"), content_type='text/html; encoding=utf-8; charset=utf-8')

            else:
                logg.error("Error in page: '%s %s', session '%s'",
                           request.type, request.fullpath, request.session.id, exc_info=1)
                s = "<pre>" + traceback.format_exc() + "</pre>"

                return request.error(500, s)

        finally:
            for handler in _request_finished_handlers:
                handler(req)


class fs:
    pass


class ftp_authorizer:

    def __init__(self):
        pass

    def authorize(self, channel, username, password):
        for handler in ftphandlers:
            fs = handler.has_user(username, password)
            if fs:
                channel.persona = -1, -1
                channel.read_only = 0
                return 1, 'Ok.', fs
        return False, "No such username/password combination", None

    def __repr__(self):
        return 'ftp_authorizer'


class zip_filesystem:

    def __init__(self, filename):
        self.filename = filename
        self.wd = '/'
        self.m = {}
        self.z = zipfile.ZipFile(filename)
        self.lock = thread.allocate_lock()
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
        self.lock.acquire()
        try:
            data = self.z.read(path)
        finally:
            self.lock.release()
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


def setBase(base):
    global GLOBAL_ROOT_DIR
    GLOBAL_ROOT_DIR = qualify_path(base)


def setTempDir(tempdir):
    global GLOBAL_TEMP_DIR
    GLOBAL_TEMP_DIR = qualify_path(tempdir)


def addFTPHandler(m):
    global ftphandlers
    ftphandlers += [m]


def addContext(webpath, localpath):
    global contexts
    c = WebContext(webpath, localpath)
    contexts += [c]
    return c

def add_wsgi_context(webpath, wsgi_app):
    c = WSGIContext(webpath, wsgi_app)
    contexts.append(c)

def setServiceUser(u):
    global service_user
    service_user = u


def setServicePwd(p):
    global service_pwd
    service_pwd = p


def flush():
    global contexts, translators, ftphandlers, global_modules
    contexts[:] = []
    translators[:] = []
    ftphandlers[:] = []
    global_modules.clear()
    _purge_all_modules()


def addFileStore(webpath, localpaths):
    global contexts
    if len(webpath) and webpath[0] != '/':
        webpath = "/" + webpath
    c = FileStore(webpath, localpaths)
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


def addFileStorePath(webpath, path):
    global contexts
    for context in contexts:
        if context.name == webpath:
            if path not in context.handlers:
                context.addRoot(path)


def setThreads(number):
    global number_of_threads
    global multithreading_enabled
    if number > 1:
        multithreading_enabled = 1
        number_of_threads = number
    else:
        multithreading_enabled = 0
        number_of_threads = 1

threadlist = None


def thread_status(req):
    req.write("""<html><head><title>Athana Status</title></head><body>""")
    if threadlist:
        i = 1
        for thread in threadlist:
            req.write("<h3>Thread %d [%s]</h3>" % (thread.number, thread.identifier))
            if thread.status == "working":
                duration = time.time() - thread.lastrequest
                if duration > 10:
                    req.write('<p style="color: red">')
                req.write("Working on <tt>%s</tt><br />" % ustr(thread.uri))
                req.write("Since: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(thread.lastrequest)))
                req.write(" (%.2f seconds)" % duration)
                if duration > 10:
                    req.write('</p>')
            else:
                if thread.duration < 10:
                    req.write('<p style="color: green">')
                req.write("Idle.<br />")
                if thread.lastrequest or thread.duration:
                    req.write("Last request <tt>%s</tt><br/>" % ustr(thread.uri))
                    req.write("Processed at: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(thread.lastrequest)) + "<br />")

                    if thread.duration >= 10:
                        req.write('<span style="color: red">Processing time: %.2f seconds</span><br />' % thread.duration)
                    else:
                        req.write("Processing time: %.2f seconds <br />" % thread.duration)

                    if thread.duration < 10:
                        req.write('</p>')
    req.write("""</body></html>""")
    req.channel.current_request = None
    req.reply_code = 200
    return req.done()

profiles = []


def profiling_status(req):
    req.write("""<html><head><title>Athana Profiling Status</title></head><body>""")

    if not profiling:
        req.write("(profiling disabled)")

    i = 1
    for time, url, trace in profiles:
        req.write("<h2>Most usage #%d</h2>" % i)
        req.write("<h3>Time: %.2f seconds</h3>" % time)
        req.write("<h3>URL: %s</h3>" % url)
        i = i + 1
        req.write('<pre>')
        req.write(attrEscape(trace))
        req.write('</pre>')

    req.write("""</body></html>""")
    req.channel.current_request = None
    req.reply_code = 200
    return req.done()

iolock = thread.allocate_lock()
profiling = 0
try:
    import hotshot
    import hotshot.stats
except ValueError:
    profiling = 0
except ImportError:
    profiling = 0


log_request_time = logg.isEnabledFor(logging.DEBUG)


class AthanaThread:

    def __init__(self, server, number):
        global profiling
        self.server = server
        self.lastrequest = 0
        self.status = "idle"
        self.number = number
        self.uri = ""
        self.duration = 0
        self.identifier = ""

    def worker_thread(self):
        server = self.server
        while 1:
            server.queuelock.acquire()
            if len(server.queue) == 0:
                server.queuelock.release()
                time.sleep(0.01)
            else:
                function, req = server.queue.pop()
                self.lastrequest = time.time()
                self.status = "working"
                self.uri = req.fullpath
                server.queuelock.release()
                if profiling:
                    self.prof = hotshot.Profile("/tmp/athana%d.prof" % self.number)
                    self.prof.start()
                    
                if log_request_time or profiling:  
                    timenow = time.time()
                try:
                    call_handler_func(server, function, req)
                except:
                    try:
                        logg.error("Error while processing request:", exc_info=1)
                    except:
                        print "FATAL ERROR: error in request, logging the exception failed!"

                if log_request_time or profiling:
                    duration = time.time() - timenow
                    logg.debug("time for request %s: %.1fms", req.path, duration * 1000.)

                if profiling:
                    global profiles
                    self.prof.stop()
                    self.prof.close()
                    st = hotshot.stats.load("/tmp/athana%d.prof" % self.number)
                    st.sort_stats('cumulative', 'time')

                    class myio:

                        def __init__(self, old):
                            self.txt = ""
                            self.old = old
                            self.id = thread.get_ident()

                        def write(self, txt):
                            if self.id == thread.get_ident():
                                self.txt += txt
                            else:
                                self.old.write(txt)

                    iolock.acquire()
                    io = myio(sys.stdout)
                    oldstdout, sys.stdout = sys.stdout, io
                    st.print_stats(50)
                    sys.stdout = oldstdout
                    iolock.release()
                    profiles += [(duration, self.uri, io.txt)]
                    profiles.sort()
                    profiles.reverse()
                    profiles = profiles[0:30]

                self.status = "idle waiting"
                self.duration = time.time() - self.lastrequest


def runthread(athanathread):
    athanathread.worker_thread()

ATHANA_STARTED = False
_ATHANA_HANDLER = None


def run(host="0.0.0.0", port=8081, z3950_port=None):
    global ATHANA_STARTED, _ATHANA_HANDLER
    check_date()
    ph = _ATHANA_HANDLER = AthanaHandler()
    hs = http_server(host, port)
    hs.install_handler(ph)

    if len(ftphandlers) > 0:
        ftp = ftp_server(ftp_authorizer(), port=ftphandlers[0].getPort())

    if z3950_port is not None:
        import athana_z3950
        z3950_server = athana_z3950.z3950_server(port=z3950_port)

    if multithreading_enabled:
        global threadlist
        threadlist = []
        for i in range(number_of_threads):
            athanathread = AthanaThread(ph, i)
            identifier = thread.start_new_thread(runthread, (athanathread,))
            athanathread.identifier = identifier
            threadlist += [athanathread]

    ATHANA_STARTED = True

    while 1:
        try:
            asyncore.loop(timeout=0.01)
        except select.error:
            continue

"""
TODO:
    * session clearup
    * temp directory in .cfg file
"""

global _test_running, _test_thread
_test_running = False
_test_thread = None

def threaded_testrun(port=8081):
    ph = AthanaHandler()
    hs = http_server('', port)
    hs.install_handler(ph)

    global _test_running, _test_thread
    _test_running = True

    def athana_test_loop():
        global ATHANA_STARTED
        ATHANA_STARTED = True

        while _test_running:
            asyncore.poll2(timeout=0.005)

        logg.info("left testmode loop")
        hs.close()

    import threading
    _test_thread = threading.Thread(target=athana_test_loop)
    _test_thread.start()

    while not ATHANA_STARTED:
        time.sleep(0.001)

    logg.info("athana testmode, use athana.stop_testrun()")


def stop_testrun():
    global _test_running
    _test_running = False
    _test_thread.join()


# COMPAT: added functions

def request_started(handler):
    """Decorator for functions which should be run before the view handler is called"""
    _request_started_handlers.append(handler)
    return handler


def request_finished(handler):
    """Decorator for functions which should be run after the view handler is called"""
    _request_finished_handlers.append(handler)
    return handler


def getBase():
    return GLOBAL_ROOT_DIR
