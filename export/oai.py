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

import base64 as _base64
import json as _json
import hashlib as _hashlib
import itertools as _itertools
import socket
import re
import time
import logging

import lxml.etree as _lxml_etree
import sqlalchemy.orm as _sqlalchemy_orm
import collections as _collections

import core.config as config
import core.httpstatus as _httpstatus

from . import oaisets
import utils.date as date
from utils.utils import esc
from schema.schema import getMetaType
from core.systemtypes import Root, Metadatatypes
from contenttypes import Collections
from core import Node
from core import db
from core.users import get_guest_user

q = db.query

logg = logging.getLogger(__name__)

FORMAT_FILTERS = {}

_error_codes = set((
    "badArgument",
    "badResumptionToken" ,
    "badVerb",
    "idDoesNotExist",
    "noRecordsMatch",
    "noPermission",
))


class _OAIError(Exception):
    def __init__(self, code, details=""):
        assert code in _error_codes
        super(_OAIError, self).__init__(code, details)
        self.code = code
        self.details = details


def registerFormatFilter(key, filterFunc, filterQuery):
    FORMAT_FILTERS[key.lower()] = {'filterFunc': filterFunc, 'filterQuery': filterQuery}


def _filter_format(node, oai_format):
    if oai_format.lower() in FORMAT_FILTERS:
        return FORMAT_FILTERS[oai_format.lower()]['filterFunc'](node)
    return True


def _write_head(params):
    resp = """<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
        <responseDate>%sZ</responseDate>
        <request""" % (_iso8601(date.now()))

    for n in params:
        resp += ' %s="%s"' % (
                    n,
                    esc(params[n]))

    resp += '>http://%s/oai/oai</request>' % config.get("host.name", socket.gethostname() + ":8081")

    return resp


def _write_tail():
    return '</OAI-PMH>'


def _iso8601(t):
    # MET summer time
    return "%0.4d-%0.2d-%0.2dT%0.2d:%0.2d:%0.2d" % (
            t.year,
            t.month,
            t.day,
            t.hour,
            t.minute,
            t.second
        )


def _parse_date(string):
    if string.endswith("Z"):
        string = string[:-1]
    try:
        return date.parse_date(string, "%Y-%m-%d")
    except:
        try:
            return date.parse_date(string, "%Y-%m-%dT%H:%M:%S")
        except:
            return date.parse_date(string[12:], "%Y-%m-%d")


def _get_export_masks(regexp):
    exportmasks = q(Node).filter(Node.a.masktype == 'export').all()
    exportmasks = [(n, n.name) for n in exportmasks if re.match(regexp, n.name) and n.type == 'mask']
    dict_metadatatype2exportmask = _collections.defaultdict(list)
    for exportmask in exportmasks:
        for parent in exportmask[0].parents:
            if parent.type == 'metadatatype':
                dict_metadatatype2exportmask[(parent, parent.name)].append(exportmask)
                break
    return dict_metadatatype2exportmask.items()


def _node_has_oai_export_mask(node, metadataformat):
    if node.getSchema() in [x[0][1] for x in _get_export_masks('oai_%s$' % metadataformat)]:
        return True
    return False


def _get_schemata_for_metadataformat(metadataformat):
    mdt_masks_list = _get_export_masks("oai_" + metadataformat.lower() + "$")  # check exact name
    schemata = [x[0][1] for x in mdt_masks_list if x[1]]
    return schemata


def _identifier_to_node(identifier):
    if not identifier:
        raise _OAIError("badArgument")
    id_prefix = config.get("oai.idprefix", "oai:mediatum.org:node/")
    if not identifier.startswith(id_prefix):
        raise _OAIError("idDoesNotExist")
    node = q(Node).get(int(identifier[len(id_prefix):]))
    if not node:
        raise _OAIError("noRecordsMatch")
    if not node.has_read_access(user=get_guest_user()):
        raise _OAIError("noPermission")
    return node


def _list_metadata_formats(params):
    if "set" in params:
        raise _OAIError("badArgument")

    # supported oai metadata formats are configured in section
    # oai.formats in the mediatum.cfg file
    d = config.getsubset('oai')
    formats = [x.strip() for x in d['formats'].split(',') if x.strip()]

    if "identifier" in params:
        node = _identifier_to_node(params.get("identifier"))
        formats = [x for x in formats if _node_has_oai_export_mask(node, x.lower())]
        formats = [x for x in formats if _filter_format(node, x.lower())]

    # write xml for metadata formats list
    res = '\n      <ListMetadataFormats>\n'

    for mdf in formats:
        res += """
         <metadataFormat>
           <metadataPrefix>%s</metadataPrefix>
           <schema>%s</schema>
           <metadataNamespace>%s</metadataNamespace>
         </metadataFormat>
         """ % (
                mdf,
                d["schema.%s" % mdf],
                d["namespace.%s" % mdf]
                )

    res += '\n</ListMetadataFormats>'

    return res


def _check_metadata_format(format):
    d = config.getsubset('oai')
    try:
        return format.lower() in [x.strip().lower() for x in d['formats'].split(',') if x.strip()]
    except:
        return False


def _identify(params):
    if tuple(params) != ("verb", ):
        raise _OAIError("badArgument")
    if config.get("config.oaibasename") == "":
        root = q(Root).one()
        name = root.getName()
    else:
        name = config.get("config.oaibasename")

    return """
            <Identify>
              <repositoryName>%s</repositoryName>
              <baseURL>%s</baseURL>
              <protocolVersion>2.0</protocolVersion>
              <adminEmail>%s</adminEmail>
              <earliestDatestamp>%s-01-01T12:00:00Z</earliestDatestamp>
              <deletedRecord>no</deletedRecord>
              <granularity>YYYY-MM-DDThh:mm:ssZ</granularity>
              <description>
                <oai-identifier xmlns="http://www.openarchives.org/OAI/2.0/oai-identifier" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai-identifier http://www.openarchives.org/OAI/2.0/oai-identifier.xsd">
                  <scheme>oai</scheme>
                  <repositoryIdentifier>%s</repositoryIdentifier>
                  <delimiter>:</delimiter>
                  <sampleIdentifier>%s</sampleIdentifier>
                </oai-identifier>
              </description>
            </Identify>""" % (
                            name,
                            config.get("host.name", socket.gethostname() + ":8081"),
                            config.get("email.admin"),
                            ustr(config.getint("oai.earliest_year", 1960) - 1),
                            config.get("host.name", socket.gethostname()),
                            config.get("oai.sample_identifier", "oai:mediatum.org:node/123")
                            )


def _get_set_specs_for_node(node):
    setspecs = oaisets.getSetSpecsForNode(node)
    setspecs_elements = ["<setSpec>%s</setSpec>" % setspec for setspec in setspecs]
    indent = '\n    '
    return indent + (indent.join(setspecs_elements))


def _get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat):
    schema = getMetaType(schema_name)
    if schema:
        mask = schema.getMask(u"oai_" + metadataformat.lower())
    else:
        mask = None
    return mask


def _write_record(node, metadataformat, mask=None):
    id_prefix = config.get("oai.idprefix", "oai:mediatum.org:node/")
    updatetime = node.get(config.get("oai.datefield", "updatetime"))
    if updatetime:
        d = _iso8601(date.parse_date(updatetime))
    else:
        d = _iso8601(date.DateTime(config.getint("oai.earliest_year", 1960) - 1, 12, 31, 23, 59, 59))

    set_specs = _get_set_specs_for_node(node)
    record_str = """
           <record>
               <header><identifier>%s</identifier>
                       <datestamp>%sZ</datestamp>
                       %s
               </header>
               <metadata>""" % (
                                id_prefix + ustr(node.id),
                                d,
                                set_specs
                                )
    assert metadataformat != "mediatum", "export/oai.py: assertion 'metadataformat != mediatum' failed"
    if mask:
        record_str += mask.getViewHTML([node], flags=8).replace('lang=""', 'lang="unknown"')
    else:
        record_str += '<recordHasNoXMLRepresentation/>'

    record_str += '</metadata></record>'

    return record_str


# exclude children of media
def _parent_is_media(n):
    try:
        p = n.getParents()[0]
        return hasattr(p, "isContainer") and p.isContainer() == 0
    except IndexError:
        logg.exception("IndexError in export.oai.parentIsMedia(...) %s %s %s %s", n, n.id, n.type, n.name)
        return True


def _retrieve_nodes(setspec, date_from, date_to, metadataformat):
    assert metadataformat

    datefield = config.get("oai.datefield", "updatetime")

    if metadataformat == 'mediatum':
        metadatatypes = q(Metadatatypes).one().children
        schemata = [m.name for m in metadatatypes if m.type == 'metadatatype' and m.name not in ['directory', 'collection']]
    else:
        schemata = _get_schemata_for_metadataformat(metadataformat)

    nodequery = oaisets.getNodesQueryForSetSpec(setspec, schemata)
    # if for this oai group set no function is defined that retrieve the nodes query, use the filters
    if not nodequery:
        collections_root = q(Collections).one()
        nodequery = collections_root.all_children
        setspecFilter = oaisets.getNodesFilterForSetSpec(setspec, schemata)
        nodequery = nodequery.filter(Node.schema.in_(schemata))
        if isinstance(setspecFilter, _collections.Iterable):
            for sFilter in setspecFilter:
                nodequery = nodequery.filter(sFilter)
        else:
            nodequery = nodequery.filter(setspecFilter)

    if date_from:
        nodequery = nodequery.filter(Node.attrs[datefield].astext >= str(date_from))
    if date_to:
        nodequery = nodequery.filter(Node.attrs[datefield].astext <= str(date_to))

    guest_user = get_guest_user()
    nodequery = nodequery.filter_read_access(user=guest_user)

    if metadataformat.lower() in FORMAT_FILTERS:
        format_string = metadataformat.lower()
        format_filter = FORMAT_FILTERS[format_string]['filterQuery']
        nodequery = nodequery.filter(format_filter)

    return nodequery


def _get_nids(metadataformat, fromParam, untilParam, setParam):
    earliest_year = config.getint("oai.earliest_year", 1960)
    date_from = None
    date_to = None
    if fromParam:
        try:
            date_from = _parse_date(fromParam)
            if date_from.year < earliest_year:
                date_from = date.DateTime(0, 0, 0, 0, 0, 0)
        except:
            raise _OAIError("badArgument")

    if untilParam:
        try:
            date_to = _parse_date(untilParam)
            if not date_to.has_time:
                date_to.hour = 23
                date_to.minute = 59
                date_to.second = 59
        except:
            raise _OAIError("badArgument")

        if date_to.year < earliest_year - 1:
            raise _OAIError("badArgument")

    if fromParam and untilParam and (fromParam > untilParam or len(fromParam) != len(untilParam)):
        raise _OAIError("badArgument")

    nodequery = _retrieve_nodes(setParam, date_from, date_to, metadataformat)
    nodequery = nodequery.filter(Node.subnode == False)
    # filter out nodes that are inactive or older versions of other nodes
    nodes = nodequery.options(_sqlalchemy_orm.load_only('id')).all()
    if not nodes:
        raise _OAIError("noRecordsMatch")

    return sorted(n.id for n in nodes)


def _get_nodes(params):
    # OAI permits to deliver only a subset of the results,
    # together with a so-called "resumption token" that may be
    # submittet in another request to retrieve more results.
    # To avoid storing informations about previous requests,
    # we encode all request parameters in the token,
    # so if the token is part of another request,
    # we can resume the response with the token string alone.
    # Besides request paramteres, the token contains the
    # current position within the list of search results,
    # and a hash of all search results.
    # The hash is needed to detect if the set of results
    # changed between requests;  if that happened,
    # we return an error as  we cannot answer the request
    # without risking inconsistencies in the results.
    if "resumptionToken" in params:
        token = params.get("resumptionToken")
        try:
            token =  _base64.b32decode(token.upper())
        except TypeError:
            raise _OAIError("badResumptionToken")
        if frozenset(params) != frozenset(("verb", "resumptionToken")):
            logg.info("OAI: getNodes: additional arguments (only verb and resumptionToken allowed)")
            raise _OAIError("badArgument")
        token = _json.loads(token)
    else:
        token = {
            "metadataPrefix": params.get("metadataPrefix"),
            "pos": 0,
            "from": params.get("from"),
            "until": params.get("until"),
            "set": params.get("set"),
        }
        if not _check_metadata_format(token["metadataPrefix"]):
            logg.info('OAI: ListRecords: metadataPrefix missing')
            raise _OAIError("badArgument")

    nids = _get_nids(token["metadataPrefix"], token["from"], token["until"], token["set"])

    logg.info("%s : set=%s, objects=%s, format=%s", params.get('verb'), token["set"], len(nids),
              token["metadataPrefix"])

    new_hash = " ".join(_itertools.imap(str, nids)).encode("ascii")
    new_hash = _base64.b64encode(_hashlib.sha512(new_hash).digest()[:8])

    if token.get("hash", new_hash) != new_hash:
        raise _OAIError("badResumptionToken")

    chunksize = config.getint("oai.chunksize", 10)
    pos = token["pos"] + chunksize
    nodes = q(Node).filter(Node.id.in_(nids[token["pos"]: pos])).all()
    metadataformat = token["metadataPrefix"]

    if pos < len(nids):
        token["hash"] = new_hash
        token["pos"] = pos
        token = _json.dumps(token)
        token = _base64.b32encode(token).lower()
        token_element = _lxml_etree.Element("resumptionToken", attrib=dict(
            expirationDate = _iso8601(date.now().add(3600 * 24)),
            completeListSize = str(len(nids)),
            cursor = str(pos),
        ))
        token_element.text = token
    else:
        token_element = None

    return nodes, token_element, metadataformat


def _list_identifiers(params):
    nodes, token, metadataformat = _get_nodes(params)
    res = '<ListIdentifiers>'

    for n in nodes:
        updatetime = n.get(config.get("oai.datefield", "updatetime"))
        if updatetime:
            d = _iso8601(date.parse_date(updatetime))
        else:
            d = _iso8601(date.now())
        res += '<header><identifier>%s</identifier><datestamp>%sZ</datestamp>%s\n</header>\n' % \
              (
              config.get("oai.idprefix", "oai:mediatum.org:node/") + ustr(n.id),
              d,
              _get_set_specs_for_node(n)
              )

    if token:
        res += _lxml_etree.tostring(token, encoding="utf8")
    res += '</ListIdentifiers>'

    return res


def _list_records(params):
    nodes, token, metadataformat = _get_nodes(params)

    res = '<ListRecords>'

    mask_cache_dict = {}
    for n in nodes:

        # retrieve mask from cache dict or insert
        schema_name = n.getSchema()
        look_up_key = u"%s_%s" % (schema_name, metadataformat)
        if look_up_key in mask_cache_dict:
            mask = mask_cache_dict.get(look_up_key)
        else:
            mask = _get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat)
            if mask:
                mask_cache_dict[look_up_key] = mask

        res += _write_record(n, metadataformat, mask=mask)

    if token:
        res += _lxml_etree.tostring(token, encoding="utf8")
    res += '</ListRecords>'

    return res


def _get_record(params):
    node = _identifier_to_node(params.get("identifier"))
    if _parent_is_media(node):
        raise _OAIError("noPermission")

    metadataformat = params.get("metadataPrefix")
    if not _check_metadata_format(metadataformat):
        raise _OAIError("badArgument")
    if metadataformat.lower() in FORMAT_FILTERS and not _filter_format(node, metadataformat.lower()):
        raise _OAIError("noPermission")

    schema_name = node.getSchema()
    mask = _get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat)

    res = '<GetRecord>'
    res += _write_record(node, metadataformat, mask=mask)
    res += '</GetRecord>'

    return res


def _list_sets():
    # new container sets may have been added
    res = '\n<ListSets>'
    for setspec, setname in oaisets.getSets():
        res += '\n <set><setSpec>%s</setSpec><setName>%s</setName></set>' % (setspec, setname)
    res += '\n</ListSets>'

    return res


def oaiRequest(req):

    start_time = time.clock()
    verb = req.params.get("verb")
    res = _write_head(req.params)
    req.response.status_code = _httpstatus.HTTP_OK
    req.response.headers['charset'] = 'utf-8'
    req.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
    try:
        if verb == "Identify":
            res += _identify(req.params)
        elif verb == "ListMetadataFormats":
            res += _list_metadata_formats(req.params)
        elif verb == "ListSets":
            res += _list_sets()
        elif verb == "ListIdentifiers":
            res += _list_identifiers(req.params)
        elif verb == "ListRecords":
            res += _list_records(req.params)
        elif verb == "GetRecord":
            res += _get_record(req.params)
        else:
            raise _OAIError("badVerb")
    except _OAIError as ex:
        req.response.status_code = _httpstatus.HTTP_BAD_REQUEST
        res += '<error code="{}">{}</error>'.format(ex.code, ex.details)

    res += _write_tail()

    logg.info("%s:%s OAI (exit after %.3f sec.) %s - (user-agent: %s)",
            req.remote_addr,
            req.port,
            (time.clock() - start_time),
            req.path.replace('//', '/'),
            req.headers.get("user-agent", "unknown")[:60],
           )

    req.response.mimetype = "application/xml"
    req.response.set_data(res)
