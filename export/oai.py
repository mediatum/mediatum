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

import socket
import re
import time
import logging
import sqlalchemy.orm as _sqlalchemy_orm
from collections import OrderedDict
import collections as _collections

import utils.utils as _utils_utils
import core.config as config
import core.httpstatus as _httpstatus

from . import oaisets
import utils.date as date
import utils.locks as _utils_lock
from utils.utils import esc
from schema.schema import getMetaType
from core.systemtypes import Root, Metadatatypes
from contenttypes import Collections
from core import Node
from core import db
from core.users import get_guest_user

q = db.query

logg = logging.getLogger(__name__)

tokenpositions = OrderedDict()

FORMAT_FILTERS = {}


def registerFormatFilter(key, filterFunc, filterQuery):
    FORMAT_FILTERS[key.lower()] = {'filterFunc': filterFunc, 'filterQuery': filterQuery}


def _filter_format(node, oai_format):
    if oai_format.lower() in FORMAT_FILTERS:
        return FORMAT_FILTERS[oai_format.lower()]['filterFunc'](node)
    return True


errordesc = {
    "badArgument": "The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.",
    "badResumptionToken": "The value of the resumptionToken argument is invalid or expired.",
    "badVerb": "none or no valid OAI verb",
    "cannotDisseminateFormat": "The metadata format identified by the value given for the metadataPrefix argument is not supported by the item or by the repository.",
    "idDoesNotExist": "The value of the identifier argument is unknown or illegal in this repository.",
    "noRecordsMatch": "The combination of the values of the from, until, set and metadataPrefix arguments results in an empty list.",
    "noMetadataFormats": "There are no metadata formats available for the specified item.",
    "noSetHierarchy": "The repository does not support sets.",
    "badDateformatUntil": "Bad argument (until): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
    "badDateformatFrom": "Bad argument (from): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
}


def _write_head(req):
    req.response.headers['charset'] = 'utf-8'
    req.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
    resp = """<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
        <responseDate>%sZ</responseDate>
        <request""" % (_iso8601(date.now()))

    for n in req.params:
        resp += ' %s="%s"' % (
                    n,
                    esc(req.params[n]))

    resp += '>http://%s/oai/oai</request>' % config.get("host.name", socket.gethostname() + ":8081")

    return resp


def _write_tail():
    return '</OAI-PMH>'


def _write_error(req, code, detail=""):
    if detail != "":
        desc = errordesc[detail]
    else:
        desc = errordesc[code]

    logg.info("%s:%s OAI (error code: %s) %s", req.remote_addr, req.port, (code),req.path.replace('//', '/'))

    return '<error code="%s">%s</error>' % (code, desc)


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
        return "badArgument"
    id_prefix = config.get("oai.idprefix", "oai:mediatum.org:node/")
    if not identifier.startswith(id_prefix):
        return "idDoesNotExist"
    node = q(Node).get(int(identifier[len(id_prefix):]))
    if not node:
        return "noRecordsMatch"
    if not node.has_read_access(user=get_guest_user()):
        return "noPermission"
    return node


def _list_metadata_formats(req):
    if "set" in req.params:
        return _write_error(req, "badArgument")

    # supported oai metadata formats are configured in section
    # oai.formats in the mediatum.cfg file
    d = config.getsubset('oai')
    formats = [x.strip() for x in d['formats'].split(',') if x.strip()]

    if "identifier" in req.params:
        node = _identifier_to_node(req.params.get("identifier"))
        if isinstance(node, str):
            return _write_error(req, node)
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


def _identify(req):
    if tuple(req.params) != ("verb", ):
        return _write_error(req, "badArgument")
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


def _new_token(params):
    token = _utils_utils.gen_secure_token()
    with _utils_lock.named_lock("oaitoken"):
        # limit length to 32
        if len(tokenpositions) >= 32:
            tokenpositions.popitem(last=False)
        tokenpositions[token] = 0

    metadataformat = params.get("metadataPrefix", None)
    return token, metadataformat


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
            return None, "badArgument"

    if untilParam:
        try:
            date_to = _parse_date(untilParam)
            if not date_to.has_time:
                date_to.hour = 23
                date_to.minute = 59
                date_to.second = 59
        except:
            return None, "badArgument"

        if date_to.year < earliest_year - 1:
            return None, "badArgument"

    if fromParam and untilParam and (fromParam > untilParam or len(fromParam) != len(untilParam)):
        return None, "badArgument"

    nodequery = _retrieve_nodes(setParam, date_from, date_to, metadataformat)
    nodequery = nodequery.filter(Node.subnode == False)
    # filter out nodes that are inactive or older versions of other nodes
    nodes = nodequery.options(_sqlalchemy_orm.load_only('id')).all()

    return tuple(n.id for n in nodes), "noRecordsMatch"


def _get_nodes(params):
    global tokenpositions
    chunksize = config.getint("oai.chunksize", 10)
    nids = None

    if "resumptionToken" in params:
        token = params.get("resumptionToken")
        if token in tokenpositions:
            pos, nids, metadataformat = tokenpositions[token]
        else:
            return None, "badResumptionToken", None
        if frozenset(params) != frozenset(("verb", "resumptionToken")):
            logg.info("OAI: getNodes: additional arguments (only verb and resumptionToken allowed)")
            return None, "badArgument", None
    else:
        token, metadataformat = _new_token(params)
        if not _check_metadata_format(metadataformat):
            logg.info('OAI: ListRecords: metadataPrefix missing')
            return None, "badArgument", None
        pos = 0

    if not nids:
        nids, code = _get_nids(metadataformat, params.get("from"), params.get("until"), params.get("set"))
    if not nids:
        return nids, code, None

    with _utils_lock.named_lock("oaitoken"):
        tokenpositions[token] = pos + chunksize, nids, metadataformat

    tokenstring = '<resumptionToken expirationDate="' + _iso8601(date.now().add(3600 * 24)) + '" ' + \
        'completeListSize="' + ustr(len(nids)) + '" cursor="' + ustr(pos) + '">' + token + '</resumptionToken>'
    if pos + chunksize >= len(nids):
        tokenstring = None
        with _utils_lock.named_lock("oaitoken"):
            del tokenpositions[token]
    logg.info("%s : set=%s, objects=%s, format=%s", params.get('verb'), params.get('set'), len(nids), metadataformat)
    res = nids[pos:pos + chunksize]
    return res, tokenstring, metadataformat


def _list_identifiers(req):
    nids, tokenstring, metadataformat = _get_nodes(req.params)

    if not nids:
        return _write_error(req, tokenstring)
    nodes = q(Node).filter(Node.id.in_(nids)).all()
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

    if tokenstring:
        res += tokenstring
    res += '</ListIdentifiers>'

    return res


def _list_records(req):
    nids, tokenstring, metadataformat = _get_nodes(req.params)
    if not nids:
        return _write_error(req, tokenstring)
    nodes = q(Node).filter(Node.id.in_(nids)).all()

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

    if tokenstring:
        res += tokenstring
    res += '</ListRecords>'

    return res


def _get_record(req):
    node = _identifier_to_node(req.params.get("identifier"))
    if isinstance(node, str):
        return _write_error(req, node)
    if _parent_is_media(node):
        return _write_error(req, "noPermission")

    metadataformat = req.params.get("metadataPrefix", None)
    if not _check_metadata_format(metadataformat):
        return _write_error(req, "badArgument")

    if metadataformat and (metadataformat.lower() in FORMAT_FILTERS) and not _filter_format(node, metadataformat.lower()):
        return _write_error(req, "noPermission")

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
    res = _write_head(req)
    req.response.status_code = _httpstatus.HTTP_OK

    if verb == "Identify":
        res += _identify(req)
    elif verb == "ListMetadataFormats":
        res += _list_metadata_formats(req)
    elif verb == "ListSets":
        res += _list_sets()
    elif verb == "ListIdentifiers":
        res += _list_identifiers(req)
    elif verb == "ListRecords":
        res += _list_records(req)
    elif verb == "GetRecord":
        res += _get_record(req)
    else:
        req.response.status_code = _httpstatus.HTTP_BAD_REQUEST
        res += _write_error(req, "badVerb")

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
