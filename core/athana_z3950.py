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

import time
import socket
import asyncore
import random # FIXME: drop dependency!

from athana import counter, async_chat, unresolving_logger
from core import tree, medmarc
from schema import mapping

from PyZ3950 import z3950, zdefs, asn1

try:
    set
except NameError:
    from sets import Set as set

class FormatError(Exception):
    """Communication format not supported.
    """

def dummy_log(*args):
    pass

class AsyncPyZ3950Server(z3950.Server):
    """Asynchronous Z3950 server implementation.

    Overrides PDU reading from socket to enable asynchronous reading.

    This is copied and adapted from z3950.py in PyZ3950.  The lifetime
    of this object is one Z39.50 session.
    """
    def __init__(self, conn, channel, logger):
        z3950.Server.__init__(self, conn)
        self.client_name = '[%s:%s]' % conn.getpeername()
        self._channel = channel
        self.logger = logger

    def _log(self, level, message, *args):
        if self.logger is None:
            return
        message = '%s:%s' % (level, (args and message % args or message))
        self.logger.log(self.client_name, message)

    def _log_debug(self, message, *args):
        self._log('debug', message, *args)

    def _log_info(self, message, *args):
        self._log('info', message, *args)

    def _log_error(self, message, *args):
        self._log('error', message, *args)

    def handle_incoming_data(self, b):
        # see classes "z3950.Server" and "z3950.Conn", methods run(), read_PDU(), readproc()
        try:
            self.decode_ctx.feed (map (ord, b))
        except asn1.BERError, val:
            raise self.ProtocolError ('ASN1 BER', str(val))
        if self.decode_ctx.val_count () > 0:
            typ, val = self.decode_ctx.get_first_decoded ()
            self._log_debug("received Z3950 message '%s'", typ)
            fn = self.fn_dict.get(typ)
            if fn is None:
                raise self.ProtocolError ("Bad typ", '%s %s' % (typ, val))
            if typ != 'initRequest' and self.expecting_init:
                raise self.ProtocolError ("Init expected", typ)
            fn (self, val)

    def send(self, val):
        b = self.encode_ctx.encode (z3950.APDU, val)
        self._channel.write(b.tostring())
        if self.done:
            self._channel.close()

    # protocol functionality

    def init (self, ireq):
        """
        Handle 'init' request after opening a connection.
        """
        # copied from "z3950.Server" to adapt options list
        self.v3_flag = (ireq.protocolVersion ['version_3'] and
                        z3950.Z3950_VERS == 3)
        
        ir = z3950.InitializeResponse ()
        ir.protocolVersion = z3950.ProtocolVersion ()
        ir.protocolVersion ['version_1'] = 1
        ir.protocolVersion ['version_2'] = 1
        ir.protocolVersion ['version_3'] = self.v3_flag
        val = zdefs.get_charset_negot (ireq)
        charset_name = None
        records_in_charsets = 0
        if val != None:
            csreq = zdefs.CharsetNegotReq ()
            csreq.unpack_proposal (val)
            def rand_choose (list_or_none):
                if list_or_none == None or len (list_or_none) == 0:
                    return None
                return random.choice (list_or_none)
            charset_name = rand_choose (csreq.charset_list)
            if charset_name != None:
                try:
                    codecs.lookup (charset_name)
                except LookupError, l:
                    charset_name = None
            csresp = CharsetNegotResp (
                charset_name,
                rand_choose (csreq.lang_list),
                csreq.records_in_charsets)
            records_in_charsets = csresp.records_in_charsets
            if trace_charset:
                print csreq, csresp
            zdefs.set_charset_negot (ir, csresp.pack_negot_resp (), self.v3_flag)
            
        optionslist = ['search', 'present', 'negotiation', 'delSet'] # , 'scan']
        ir.options = z3950.Options ()
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
        self.send (('initResponse', ir))
        self.set_codec (charset_name, records_in_charsets)

    def search_child(self, query):
        """
        Parse an incoming query and run a node search for it.  Returns
        the matching node IDs.  Called by base class implementation of
        'search' request handler.
        """
        self._log_info(query)
        try:
            parsed_query = parse_rpn_query(query)
        except Exception, e:
            self._log_error("error (%s) while unpacking Z3950 search query: %s", e, query)
            raise
        self._log_debug('%r', parsed_query)
        node_ids = search_nodes(parsed_query, self._log)
        #node_ids = search_nodes('1004 = "Kramm, Matthias"', self._log)
        self._log_debug('IDs returned for Z3950 query: %s', len(node_ids))
        return node_ids

    def format_records (self, start, count, res_set, prefsyn):
        """
        Format a 'present' response for the requested query result subset.
        """
        #encode_charset = self.charset_name
        map_node = medmarc.MarcMapper()
        l = []
        for i in xrange(start-1, min(len(res_set), start+count-1)):
            try:
                node = tree.getNode( res_set[i] )
            except tree.NoSuchNodeError:
                self._log_debug("request for non-existant node %s", res_set[i])
                continue
            marc21_node = map_node(node)
            if marc21_node is None:
                # no mapping => no node
                continue
            elt_external = asn1.EXTERNAL()
            elt_external.direct_reference = z3950.Z3950_RECSYN_USMARC_ov
            elt_external.encoding = ('octet-aligned', marc21_node)
            n = z3950.NamePlusRecord()
            n.name = str(node.id)
            n.record = ('retrievalRecord', elt_external)
            l.append(n)
        return l

    def delete (self, dreq):
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
        self.send (('deleteResultSetResponse', dresp))

    fn_dict = {
        'searchRequest': z3950.Server.search,
        'presentRequest': z3950.Server.present,
        'initRequest' : init,
        'close' : z3950.Server.close,
        #'sortRequest' : sort,
        'deleteResultSetRequest' : delete,
        #'extendedServicesRequest': esrequest
        }

# Query support

def search_nodes(query, log=dummy_log, mapping_prefix='Z3950_search_'):
#def search_nodes(query, log=dummy_log, mapping_prefix='marc21_'):
    """
    Search nodes that match the query.

    'query' is a tree of QueryBoolNode and QueryMatchNode objects.

    Query root nodes are configured by a naming convention.  The names
    of mappings that starting with the given 'mapping_prefix' must end
    with a node ID, which is then used as root node for the search
    based on that field mapping.
    """
    # find root nodes and their mappings
    roots_and_mappings = []
    for mapping_node in mapping.getMappings():
        #print [x.getName() for x in mapping.getMappings()]
        name = mapping_node.getName()
        if not name.startswith(mapping_prefix):
            continue
        try:
            node_id = name[len(mapping_prefix):]
            roots_and_mappings.append((tree.getNode(node_id), mapping_node))
        except tree.NoSuchNodeError:
            log('error',
                ("Configuration problem detected: Z39.50 search mapping '%s' found, "
                 "but no matching root node with ID '%s'"),
                name, node_id)

    if not roots_and_mappings:
        log('info', 'no mappings configured, skipping search')
        return []

    log('debug', 'using mapping roots: %s' % (
        [ (n1.id, n2.id) for (n1,n2) in roots_and_mappings ],))
        
    # run one search per root node
    node_ids = []
    for root_node, mapping_node in roots_and_mappings:
        # map query fields to node attributes
        field_mapping = {}
        for field in mapping_node.getChildren():
            field_mapping[field.getName()] = field.getDescription().split(';')
        # FIXME: this is redundant - why build an infix query string
        # just to parse it afterwards?
        query_string = query.build_query_string(field_mapping)
        if query_string is None:
            log('info', 'unable to map query: [%r] using mapping %s' % (query, field_mapping))
            continue
        log('info', 'executing query: %s', query_string)
        node_ids.append( root_node.search(query_string).getIDs() )

    # use a round-robin algorithm to merge the separate query results
    # in order to produce maximally diverse results in the first hits
    return merge_ids_as_round_robin(node_ids)

def merge_ids_as_round_robin(id_sets):
    """
    Round robin merge of multiple ID sets.

    Examples::

        >>> merge_ids_as_round_robin([('1','2'), ('3','4','5'), (), ('6',)])
        ['1', '3', '6', '2', '4', '5']
    """
    nexts = [ iter(id_set).next for id_set in id_sets if id_set ]
    seen = set()
    ids = []
    to_drop = []
    while nexts:
        for next_from_set in nexts:
            try:
                next_id = next_from_set()
            except StopIteration:
                to_drop.append(next_from_set)
            else:
                if next_id not in seen:
                    seen.add(next_id)
                    ids.append(next_id)
        if to_drop:
            for next_func in to_drop:
                nexts.remove(next_func)
            del to_drop[:]
    return ids

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
        left  = self.left.build_query_string(field_mapping)
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
        self.op, self.name, self.value = op, name, protect(value)

    def build_query_string(self, field_mapping):
        if self.name not in field_mapping:
            return None
        op, value = self.op, self.value
        return ' or '.join([ '%s %s %s' % (field_type, op, value)
                             for field_type in field_mapping[self.name] ])

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
        if attr.attributeType == 1: # 'use' attribute
            attr_type, value = attr.attributeValue
            if attr_type == 'numeric':
                cmp_value = str(value)
        elif attr.attributeType == 2: # 'relation' attribute
            attr_type, value = attr.attributeValue
            if attr_type == 'numeric' and 1 <= value <= 6:
                op = ('<', '<=', '=', '>=', '>', '!=')[value-1]
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
            if r_op == 'and_not': r_op = 'and not'
            return QueryBoolNode(r_op, a1, a2)

    return recursive_parse(rpn_query.rpn)


# Athana support

class z3950_channel(async_chat):
    ac_in_buffer_size       = 4096
    ac_out_buffer_size      = 4096

    def __init__(self, server, conn, addr, logger):
        self.server = server
        async_chat.__init__ (self, conn)

        push = self.push

        class ChannelInterface(object):
            def write(self, data):
                server.total_bytes_out.increment(len(data))
                push(data)
            def close(self):
                server.closed_sessions.increment()
                server.close_when_done()
        
        self.z3950_server = AsyncPyZ3950Server(conn, ChannelInterface(), logger)

    def readable(self):
        return 1 # always

    def handle_read(self):
        try:
            data = self.recv(self.ac_in_buffer_size)
            self.server.total_bytes_in.increment(len(data))
            self.z3950_server.handle_incoming_data(data)
        except:
            self.server.total_exceptions.increment()
            self.handle_error()
            self.close()


class z3950_server(asyncore.dispatcher):
    z3950_channel_class = z3950_channel

    def __init__ (self, ip='', port=2101, logger_object=None):
        self.ip = ip
        self.port = port

        # statistics
        self.total_sessions = counter()
        self.closed_sessions = counter()
        self.total_bytes_out = counter()
        self.total_bytes_in = counter()
        self.total_exceptions = counter()
        #
        asyncore.dispatcher.__init__ (self)
        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)

        self.set_reuse_addr()
        self.bind ((self.ip, self.port))
        self.listen (5)

        if logger_object is None:
            logger_object = sys.stdout

        self.logger = unresolving_logger (logger_object)
        
        self.log_info = self.logger.log_func        

        self.log_info('Z3950 server started at %s, Port: %d\n' % (
                time.ctime(time.time()),
                self.port)
                )
                

    def handle_accept(self):
        conn, addr = self.accept()
        self.total_sessions.increment()
        self.log_info('Incoming connection from %s:%d' % (addr[0], addr[1]))
        self.z3950_channel_class(self, conn, addr, self.logger)

    def writable (self):
        return 0

    def handle_read (self):
        pass

    def readable (self):
        return self.accepting
