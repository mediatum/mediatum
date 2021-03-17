"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Stefan Behnel <stefan_ml@behnel.de>

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
from __future__ import division
from __future__ import print_function

import codecs
import collections as _collections
import logging
import socket
import asyncore

from PyZ3950 import z3950, zdefs, asn1
from sqlalchemy.orm import undefer
from core.search.config import get_service_search_languages
from utils.utils import suppress
import core as _core
import core.config as _config
import schema as _schema


logg = logging.getLogger(__name__)


class z3950_channel(asyncore.dispatcher):

    """This is an abstract class.  You must derive from this class, and add
    the two methods collect_incoming_data() and found_terminator()"""

    # these are overridable defaults

    ac_in_buffer_size = 4096
    ac_out_buffer_size = 4096

    def __init__(self, conn=None):
        self.ac_in_buffer = ''
        self.ac_out_buffer = ''
        self.producer_fifo = _collections.deque()
        asyncore.dispatcher.__init__(self, conn)
        self.z3950_server = AsyncPyZ3950Server(conn, _ChannelInterface(self))

    def collect_incoming_data(self, data):
        raise NotImplementedError("must be implemented in subclass")

    def found_terminator(self):
        raise NotImplementedError("must be implemented in subclass")

    def set_terminator(self, term):
        "Set the input delimiter.  Can be a fixed string of any length, an integer, or None"
        self.terminator = term

    def get_terminator(self):
        return self.terminator

    def handle_read(self):
        data = '--- not read ---'
        try:
            data = self.recv(self.ac_in_buffer_size)
            logg.debug('received %i bytes of data: %r', len(data), data)
            if data and self.connected:
                self.z3950_server.handle_incoming_data(data)
        except:
            logg.exception('handle_read %i bytes of data: %r', len(data), data)
            self.handle_error()
            self.close()

    def handle_write(self):
        self.initiate_send()

    def handle_close(self):
        self.close()

    def push(self, data):
        self.producer_fifo.append(simple_producer(data))
        self.initiate_send()

    def push_with_producer(self, producer):
        self.producer_fifo.append(producer)
        self.initiate_send()

    def readable(self):
        return 1

    def writable(self):
        "predicate for inclusion in the writable for select()"
        # return len(self.ac_out_buffer) or len(self.producer_fifo) or (not self.connected)
        # this is about twice as fast, though not as clear.
        return not (
            (self.ac_out_buffer == '') and
            not self.producer_fifo and
            self.connected
        )

    def close_when_done(self):
        "automatically close this channel once the outgoing queue is empty"
        self.producer_fifo.append(None)

    # refill the outgoing buffer by calling the more() method
    # of the first producer in the queue
    def refill_buffer(self):
        while 1:
            if self.producer_fifo:
                p = self.producer_fifo[0]
                # a 'None' in the producer fifo is a sentinel,
                # telling us to close the channel.
                if p is None:
                    if not self.ac_out_buffer:
                        self.producer_fifo.popleft()
                        try:
                            self.close()
                        except KeyError:
                            # FIXME: tends to happen sometimes, seems to
                            # be a race condition in asyncore
                            with suppress(Exception, warn=False):
                                self._fileno = None
                                self.socket.close()
                    return
                elif isinstance(p, str):
                    self.producer_fifo.popleft()
                    self.ac_out_buffer = self.ac_out_buffer + p
                    return
                data = p.more()
                if data:
                    self.ac_out_buffer = self.ac_out_buffer + data
                    return
                else:
                    self.producer_fifo.popleft()
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
        self.producer_fifo.clear()


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


def format_node(node, map_node):
    marc21_node = map_node(node)

    # None? no mapping => no node
    if marc21_node is not None:
        elt_external = asn1.EXTERNAL()
        elt_external.direct_reference = z3950.Z3950_RECSYN_USMARC_ov
        elt_external.encoding = ('octet-aligned', marc21_node)
        n = z3950.NamePlusRecord()
        n.name = unicode(node.id)
        n.record = ('retrievalRecord', elt_external)
        return n


class AsyncPyZ3950Server(z3950.Server):

    """Asynchronous Z3950 server implementation.

    Overrides PDU reading from socket to enable asynchronous reading.

    This is copied and adapted from z3950.py in PyZ3950.  The lifetime
    of this object is one Z39.50 session.
    """

    def __init__(self, conn, channel):
        z3950.Server.__init__(self, conn)
        self.client_name = '[%s:%s]' % conn.getpeername()
        self._channel = channel

    def handle_incoming_data(self, b):
        # see classes "z3950.Server" and "z3950.Conn", methods run(), read_PDU(), readproc()
        try:
            self.decode_ctx.feed(map(ord, b))
        except asn1.BERError, val:
            raise self.ProtocolError('ASN1 BER', unicode(val))
        if self.decode_ctx.val_count() > 0:
            typ, val = self.decode_ctx.get_first_decoded()
            logg.debug("received Z3950 message '%s'", typ)
            fn = self.fn_dict.get(typ)
            if fn is None:
                raise self.ProtocolError("Bad typ", '%s %s' % (typ, val))
            if typ != 'initRequest' and self.expecting_init:
                raise self.ProtocolError("Init expected", typ)
            try:
                fn(self, val)
            except:
                logg.exception("error while handling request")

    def send(self, val):
        b = self.encode_ctx.encode(z3950.APDU, val)
        self._channel.write(b.tostring())
        if self.done:
            self._channel.close()

    # protocol functionality

    def init(self, ireq):
        """
        Handle 'init' request after opening a connection.
        """
        # copied from "z3950.Server" to adapt options list
        self.v3_flag = (ireq.protocolVersion['version_3'] and
                        z3950.Z3950_VERS == 3)

        ir = z3950.InitializeResponse()
        ir.protocolVersion = z3950.ProtocolVersion()
        ir.protocolVersion['version_1'] = 1
        ir.protocolVersion['version_2'] = 1
        ir.protocolVersion['version_3'] = self.v3_flag

        optionslist = ['search', 'present', 'negotiation', 'delSet']  # , 'scan']
        ir.options = z3950.Options()
        for o in optionslist:
            ir.options[o] = 1

        ir.preferredMessageSize = 0

        ir.exceptionalRecordSize = 0
        # z9350-2001 3.2.1.1.4, 0 means client should be prepared to accept
        # arbitrarily long messages.

        ir.implementationId = "mediaTUM Z39.50 Server (no official ID)"

        ir.implementationName = 'mediaTUM'
        ir.implementationVersion = zdefs.impl_vers
        ir.result = 1

        self.expecting_init = 0
        self.send(('initResponse', ir))

    def search_child(self, query):
        """
        Parse an incoming query and run a node search for it.  Returns
        the matching node IDs.  Called by base class implementation of
        'search' request handler.
        """
        logg.debug("query: %s", query)
        try:
            parsed_query = parse_rpn_query(query)
        except Exception:
            logg.exception("error while unpacking Z3950 search query '%s':", query)
            raise
        logg.debug('%r', parsed_query)
        node_ids = search_nodes(parsed_query)  # , self._log)
        logg.debug('IDs returned for Z3950 query: %s', len(node_ids))
        return node_ids

    def format_records(self, start, count, res_set, prefsyn):
        """
        Format a 'present' response for the requested query result subset.
        """
        map_node = _core.medmarc.MarcMapper()

        node_ids = res_set[start-1:start+count-1]
        nodes = _core.db.query(_core.Node).filter(_core.Node.id.in_(node_ids)).prefetch_attrs()
        formatted = [fo for fo in [format_node(n, map_node) for n in nodes] if fo is not None]
        return formatted

    def delete(self, dreq):
        """
        Handle a 'delete' request to explicitly drop an item from the
        list of recent query results.
        """
        failures = 0
        for result in dreq.resultSetList:
            try:
                del self.result_sets[result]
            except KeyError:
                failures += 1
        dresp = z3950.DeleteResultSetResponse()
        dresp.deleteOperationStatus = 0
        self.send(('deleteResultSetResponse', dresp))

    fn_dict = {
        'searchRequest': z3950.Server.search,
        'presentRequest': z3950.Server.present,
        'initRequest': init,
        'close': z3950.Server.close,
        #'sortRequest' : sort,
        'deleteResultSetRequest': delete,
        #'extendedServicesRequest': esrequest
    }

# Query support


def search_nodes(query, mapping_prefix='Z3950_search_'):
    """
    Search nodes that match the query.

    'query' is a tree of QueryBoolNode and QueryMatchNode objects.

    Query root nodes are configured by a naming convention.  The names
    of mappings that starting with the given 'mapping_prefix' must end
    with a node ID, which is then used as root node for the search
    based on that field mapping.
    """
    import core.database.postgres.search as _postgres_search

    def get_root_for_mapping(mapping_node):
        name = mapping_node.name
        node_id = name[len(mapping_prefix):]
        node = _core.db.query(_core.Node).get(node_id)
        return node

    def filter_dbquery_results(dbquery):
        return dbquery.filter_read_access(user=guest)

    mapping_nodes = _core.db.query(_schema.mapping.Mapping).filter(_schema.mapping.Mapping.name.startswith(mapping_prefix))
    roots_and_mappings = [(get_root_for_mapping(m), m) for m in mapping_nodes]

    if not roots_and_mappings:
        logg.info('no mappings configured, skipping search')
        return []

    logg.debug('using mapping roots: %s', [(n1.id, n2.id) for (n1, n2) in roots_and_mappings])

    # run one search per root node
    node_ids = []
    guest = _core.users.get_guest_user()
    search_languages = get_service_search_languages()

    for root_node, mapping_node in roots_and_mappings:
        if root_node is None:
            logg.error("Configuration problem detected: Z39.50 search mapping '%s' found, but no matching root node", mapping_node.name)
            continue
        # map query fields to node attributes
        field_mapping = {}
        for field in mapping_node.children:
            field_mapping[field.name] = field.getDescription().split(';')
        # XXX: this is redundant - why build an infix query string
        # XXX: just to parse it afterwards?
        # XXX: better: create search tree and apply it to a query instead of using node.search()
        query_string = query.build_query_string(field_mapping)
        searchtree = _core.search.parse_searchquery_old_style(query_string)
        if query_string is None:
            logg.info('unable to map query: [%r] using mapping %s', query, field_mapping)
            continue
        logg.info('executing query for node %s: %s', root_node.id, query_string)
        _postgres_search.set_session_timeout(_config.getint('search.timeout_z3950', 600))
        for n in root_node.search(searchtree, search_languages, filter_dbquery=filter_dbquery_results):
            node_ids.append(n.id)

    # use a round-robin algorithm to merge the separate query results
    # in order to produce maximally diverse results in the first hits
    return node_ids


def protect(s):
    """
    Wrap a string in double quotes, dropping contained double quotes
    if available.
    """
    return '"%s"' % s.replace('"', '')


class QueryBoolNode(object):

    "and/or node"

    def __init__(self, op, left, right):
        self.op, self.left, self.right = op, left, right

    def build_query_string(self, field_mapping):
        left = self.left.build_query_string(field_mapping)
        right = self.right.build_query_string(field_mapping)
        if left and right:
            return '(%s) %s (%s)' % (left, self.op, right)
        else:
            return left or right

    def __repr__(self):
        return '(%r) %s (%r)' % (self.left, self.op, self.right)


class QueryMatchNode(object):

    "equality match"

    def __init__(self, op, name, value):
        self.op, self.name, self.value = op, name, protect(value).decode('utf8')

    def build_query_string(self, field_mapping):
        if self.name not in field_mapping:
            return None
        op, value = self.op, self.value
        return ' or '.join(['%s %s %s' % (field_type, op, value)
                            for field_type in field_mapping[self.name]])

    def __repr__(self):
        return '%s = %s' % (self.name, self.value)


def find_query_attribute(attrs):
    """
    Bib-1 attribute types
    1=Use:         4=Title 7=ISBN 8=ISSN 30=Date 62=Abstract 1003=Author 1016=Any
    2=Relation:    1<   2<=  3=  4>=  5>  6!=  102=Relevance
    3=Position:    1=First in Field  2=First in subfield  3=Any position
    4=Structure:   1=Phrase  2=Word  3=Key  4=Year  5=Date  6=WordList
    5=Truncation:  1=Right  2=Left  3=L&R  100=No  101=#  102=Re-1  103=Re-2
    6=Completeness:1=Incomplete subfield  2=Complete subfield  3=Complete field
    """
    cmp_value = None
    op = '='
    for attr in attrs:
        if attr.attributeType == 1:  # 'use' attribute
            attr_type, value = attr.attributeValue
            if attr_type == 'numeric':
                cmp_value = unicode(value)
        elif attr.attributeType == 2:  # 'relation' attribute
            attr_type, value = attr.attributeValue
            if attr_type == 'numeric' and 1 <= value <= 6:
                op = ('<', '<=', '=', '>=', '>', '!=')[value - 1]
    if cmp_value and op:
        return cmp_value, op
    raise ValueError("no 'use' or 'relation' attribute found in query term")


def parse_rpn_query(query):
    """Parse RPN query into a tree of QueryBoolNode and QueryMatchNode objects.
    """
    query_type, rpn_query = query
    if query_type not in ('type_1', 'type_2'):
        raise ValueError("query has unsupported type '%s'" % query_type)

    def recursive_parse(q):
        # ignore attributeSet
        typ, val = q
        if typ == 'op':
            if val[0] != 'attrTerm':
                raise ValueError("unsupported attribute set found: '%s'" % val[0])
            val = val[1]
            term_type, op = find_query_attribute(val.attributes)
            return QueryMatchNode(op, term_type, val.term[1])
        else:
            a1 = recursive_parse(val.rpn1)
            a2 = recursive_parse(val.rpn2)
            r_op = val.op[0]
            if val.op[1] is not None:
                raise ValueError("and/or term has unexpected format")
            if r_op == 'and_not':
                r_op = 'and not'
            return QueryBoolNode(r_op, a1, a2)

    return recursive_parse(rpn_query.rpn)


class _ChannelInterface(object):

    def __init__(self, channel):
        self._channel = channel

    def write(self, data):
        self._channel.push(data)

    def close(self):
        self._channel.close_when_done()


class z3950_server(asyncore.dispatcher):
    z3950_channel_class = z3950_channel

    def __init__(self, ip='', port=2101):
        self.ip = ip
        self.port = port

        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        self.set_reuse_addr()
        self.bind((self.ip, self.port))
        self.listen(5)

        logg.info('Z3950 server started, Port: %d\n', self.port)

    def handle_accept(self):
        conn, addr = self.accept()
        logg.info('Incoming connection from %s:%d', addr[0], addr[1])
        self.z3950_channel_class(conn)

    def writable(self):
        return 0

    def handle_read(self):
        pass

    def readable(self):
        return self.accepting
