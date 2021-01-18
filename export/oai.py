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
import utils.lrucache as _utils_lrucache
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


def _make_toplevel_element(**params):
    xsi_schemaLocation = _lxml_etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
    oai_pmh = _lxml_etree.Element('OAI-PMH', nsmap={
        None: "http://www.openarchives.org/OAI/2.0/",
    }, attrib={
        xsi_schemaLocation: "http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd",
    })

    _lxml_etree.SubElement(oai_pmh, "responseDate").text = "{}Z".format(_iso8601(date.now()))
    _lxml_etree.SubElement(oai_pmh, "request", attrib=dict(params)).text = \
        'http://{}/oai/oai'.format(config.get("host.name", "{}:8081".format(socket.gethostname())))

    return oai_pmh


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


def _yield_export_mask_metatype_names(metadataformat):
    re_mdf = re.compile("oai_{}$".format(metadataformat.lower())).match
    for exportmask in q(Node).filter(Node.a.masktype == 'export').all():
        if re_mdf(exportmask.name) and exportmask.type == "mask":
            for parent in exportmask.parents:
                if parent.type == 'metadatatype':
                    yield parent.name
                    break


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


def _list_metadata_formats(identifier=None, **excess):
    if excess:
        raise _OAIError("badArgument")

    # supported oai metadata formats are configured in section
    # oai.formats in the mediatum.cfg file
    d = config.getsubset('oai')
    formats = (x.strip() for x in d['formats'].split(','))
    formats = _itertools.ifilter(None,formats)  # drop empty elements

    if identifier:
        node = _identifier_to_node(identifier)
        formats = (x for x in formats if node.getSchema() in _yield_export_mask_metatype_names(x))
        formats = (x for x in formats if _filter_format(node, x.lower()))

    list_metadata_formats = _lxml_etree.Element("ListMetadataFormats")

    for mdf in formats:
        metadata_format = _lxml_etree.SubElement(list_metadata_formats, "metadataFormat")
        _lxml_etree.SubElement(metadata_format, "metadataPrefix").text = mdf
        _lxml_etree.SubElement(metadata_format, "schema").text = d["schema.{}".format(mdf)]
        _lxml_etree.SubElement(metadata_format, "metadataNamespace").text = d["namespace.{}".format(mdf)]

    return list_metadata_formats

def _check_metadata_format(format):
    d = config.getsubset('oai')
    try:
        return format.lower() in [x.strip().lower() for x in d['formats'].split(',') if x.strip()]
    except:
        return False


def _identify(**excess):
    if excess:
        raise _OAIError("badArgument")
    name = config.get("config.oaibasename")
    if not name:
        root = q(Root).one()
        name = root.getName()

    identify = _lxml_etree.Element("Identify")

    for tag, txt in (
        ("repositoryName", name),
        ("baseURL", 'http://{}/oai/oai'.format(config.get("host.name", "{}:8081".format(socket.gethostname())))),
        ("protocolVersion", "2.0"),
        ("adminEmail", config.get("email.admin")),
        ("earliestDatestamp", "{}-01-01T12:00:00Z".format(ustr(config.getint("oai.earliest_year", 1960) - 1))),
        ("deletedRecord", "no"),
        ("granularity", "YYYY-MM-DDThh:mm:ssZ"),
    ):
        _lxml_etree.SubElement(identify, tag).text = txt

    description = _lxml_etree.SubElement(identify, "description")

    xsi_schemaLocation = _lxml_etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
    oai_identifier = _lxml_etree.SubElement(description, "oai-identifier", nsmap={
        None: "http://www.openarchives.org/OAI/2.0/oai-identifier",
    }, attrib={
        xsi_schemaLocation: "http://www.openarchives.org/OAI/2.0/oai-identifier "
                    "http://www.openarchives.org/OAI/2.0/oai-identifier.xsd",
    })

    for tag, txt in (
        ("scheme", "oai"),
        ("repositoryIdentifier", config.get("host.name", socket.gethostname())),
        ("delimiter", ":"),
        ("sampleIdentifier", config.get("oai.sample_identifier", "oai:mediatum.org:node/123")),
    ):
        _lxml_etree.SubElement(oai_identifier, tag).text = txt

    return identify


def _get_header_element(id_prefix, date, node):
    header = _lxml_etree.Element("header")
    _lxml_etree.SubElement(header, "identifier").text = "{}{}".format(id_prefix, ustr(node.id))
    _lxml_etree.SubElement(header, "datestamp").text = "{}Z".format(date)
    setspecs = oaisets.getSetSpecsForNode(node)
    for setspec in setspecs:
        _lxml_etree.SubElement(header, "setSpec").text = setspec
    return header


def _get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat):
    schema = getMetaType(schema_name)
    if schema:
        return schema.getMask(u"oai_{}".format(metadataformat.lower()))


def _make_record_element(node, metadataformat, mask=None):
    id_prefix = config.get("oai.idprefix", "oai:mediatum.org:node/")
    updatetime = node.get(config.get("oai.datefield", "updatetime"))
    if updatetime:
        d = _iso8601(date.parse_date(updatetime))
    else:
        d = _iso8601(date.DateTime(config.getint("oai.earliest_year", 1960) - 1, 12, 31, 23, 59, 59))

    record = _lxml_etree.Element("record")
    header = _get_header_element(id_prefix, d, node)
    record.append(header)

    metadata = _lxml_etree.SubElement(record, "metadata")
    assert metadataformat != "mediatum", "export/oai.py: assertion 'metadataformat != mediatum' failed"
    if mask:
        html_tree = mask.getViewHTML([node], flags=8).replace('lang=""', 'lang="unknown"')
        if html_tree:
            html_tree = _lxml_etree.fromstring(html_tree.encode("utf-8"))
            metadata.append(html_tree)
            return record

    _lxml_etree.SubElement(metadata, "recordHasNoXMLRepresentation")
    return record


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
        schemata = list(_yield_export_mask_metatype_names(metadataformat))

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


def _get_nodes(set_param=None, metadataPrefix=None, date_from=None, until=None, resumptionToken=None):
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
    if resumptionToken:
        try:
            token =  _base64.b32decode(resumptionToken.upper())
        except TypeError:
            raise _OAIError("badResumptionToken")
        if metadataPrefix or date_from or until:
            raise _OAIError("badArgument")
        token = _json.loads(token)
    else:
        token = {
            "metadataPrefix": metadataPrefix,
            "pos": 0,
            "from": date_from,
            "until": until,
            "set": set_param,
        }
        if not _check_metadata_format(token["metadataPrefix"]):
            logg.info('OAI: ListRecords: metadataPrefix missing')
            raise _OAIError("badArgument")

    nids = _get_nids(token["metadataPrefix"], token["from"], token["until"], token["set"])

    logg.info("_get_nodes : set=%s, objects=%s, format=%s", token["set"], len(nids), token["metadataPrefix"])

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


def _list_identifiers(set=None, metadataPrefix=None, until=None, resumptionToken=None, **excess):
    from_ = excess.pop("from", None)
    if excess:
        raise _OAIError("badArgument")
    nodes, token, metadataformat = _get_nodes(set, metadataPrefix, from_, until, resumptionToken)
    list_identifiers = _lxml_etree.Element("ListIdentifiers")
    for n in nodes:
        updatetime = n.get(config.get("oai.datefield", "updatetime"))
        if updatetime:
            d = _iso8601(date.parse_date(updatetime))
        else:
            d = _iso8601(date.now())
        header = _get_header_element(config.get("oai.idprefix", "oai:mediatum.org:node/"), d, n)
        list_identifiers.append(header)
    if token is not None:
        list_identifiers.append(token)

    return list_identifiers


def _list_records(set=None, metadataPrefix=None, until=None, resumptionToken=None, **excess):
    from_ = excess.pop("from", None)
    if excess:
        raise _OAIError("badArgument")
    nodes, token, metadataformat = _get_nodes(set, metadataPrefix, from_, until, resumptionToken)
    list_records = _lxml_etree.Element("ListRecords")
    get_mask = _utils_lrucache.lru_cache()(_get_oai_export_mask_for_schema_name_and_metadataformat)
    for n in nodes:
        list_records.append(_make_record_element(n, metadataformat, mask=get_mask(n.getSchema(), metadataformat)))
    if token is not None:
        list_records.append(token)

    return list_records


def _get_record(identifier=None, metadataPrefix=None , **excess):
    if excess or (None in (identifier, metadataPrefix)):
        raise _OAIError("badArgument")
    node = _identifier_to_node(identifier)
    if _parent_is_media(node):
        raise _OAIError("noPermission")

    metadataformat = metadataPrefix
    if not _check_metadata_format(metadataformat):
        raise _OAIError("badArgument")
    if metadataformat.lower() in FORMAT_FILTERS and not _filter_format(node, metadataformat.lower()):
        raise _OAIError("noPermission")

    schema_name = node.getSchema()
    mask = _get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat)
    get_record = _lxml_etree.Element("GetRecord")
    get_record.append(_make_record_element(node, metadataformat, mask=mask))
    return get_record


def _list_sets(resumptionToken=None, **excess):
    if resumptionToken:
        raise _OAIError("badResumptionToken")
    if excess:
        raise _OAIError("badArgument")
    list_sets = _lxml_etree.Element("ListSets")
    for setspec, setname in oaisets.getSets():
        set = _lxml_etree.SubElement(list_sets, "set")
        _lxml_etree.SubElement(set, "setSpec").text = setspec
        _lxml_etree.SubElement(set, "setName").text = setname
    return list_sets


_verb_handlers = dict(
        Identify=_identify,
        ListMetadataFormats=_list_metadata_formats,
        ListSets=_list_sets,
        ListIdentifiers=_list_identifiers,
        ListRecords=_list_records,
        GetRecord=_get_record
)


def oaiRequest(req):

    start_time = time.clock()

    params = dict(req.params)
    oai_pmh = _make_toplevel_element(**params)
    verb = params.pop("verb", None)

    req.response.status_code = _httpstatus.HTTP_OK
    req.response.headers['charset'] = 'utf-8'
    req.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
    try:
        if verb in _verb_handlers:
            oai_pmh.append(_verb_handlers[verb](**params))
        else:
            raise _OAIError("badVerb")
    except _OAIError as ex:
        if ex.code in ("badArgument", "badVerb"):
            oai_pmh = _make_toplevel_element()
        req.response.status_code = _httpstatus.HTTP_BAD_REQUEST
        error = _lxml_etree.Element("error", attrib=dict(code= ex.code,))
        error.text = ex.details
        oai_pmh.append(error)

    logg.info("%s OAI (exit after %.3f sec.) %s - (user-agent: %s)",
            req.remote_addr,
            (time.clock() - start_time),
            req.path.replace('//', '/'),
            req.headers.get("user-agent", "unknown")[:60],
           )

    res = _lxml_etree.tostring(oai_pmh, encoding='utf-8', method="xml", xml_declaration=True, pretty_print=True)
    req.response.mimetype = "text/xml"
    req.response.set_data(res)
