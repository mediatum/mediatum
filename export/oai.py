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
import random
import re
import time
import logging
from collections import OrderedDict

import core.config as config

from .oaisearchparser import OAISearchParser as OAISearchParser
from . import oaisets
import utils.date as date
import core.xmlnode
from utils.utils import esc
from schema.schema import getMetaType
from utils.pathutils import isDescendantOf
from threading import Lock
from core.systemtypes import Root, Metadatatypes
from contenttypes import Collections
from core import Node
from core import db
from core.users import get_guest_user

q = db.query

logg = logging.getLogger(__name__)


DEBUG = True

DATEFIELD = config.get("oai.datefield", "updatetime")
EARLIEST_YEAR = int(config.get("oai.earliest_year", "1960"))
CHUNKSIZE = int(config.get("oai.chunksize", "10"))
IDPREFIX = config.get("oai.idprefix", "oai:mediatum.org:node/")
SAMPLE_IDENTIFIER = config.get("oai.sample_identifier", "oai:mediatum.org:node/123")
tokenpositions = OrderedDict()
token_lock = Lock()

SET_LIST = []
FORMAT_FILTERS = {}


def registerFormatFilter(key, filterFunc, filterQuery):
    FORMAT_FILTERS[key.lower()] = {'filterFunc': filterFunc, 'filterQuery': filterQuery}


def filterFormat(node, oai_format):
    if oai_format.lower() in FORMAT_FILTERS.keys():
        return FORMAT_FILTERS[oai_format.lower()]['filterFunc'](node)
    return True


def now():
    return time.clock()


def make_lookup_key(req):
    return "%s:%d" % (req.ip, req.channel.addr[1])


def timetable_update(req, msg):
    if req:
        req._tt['tlist'].append((msg, now()))


def timetable_string(req):
    s = '' + ('-' * 80)
    s += "\n| timetable for request %s" % (req.uri)
    atime = req._tt['atime']
    count = 0
    for i, (msg, t) in enumerate(req._tt['tlist']):
        duration = t - atime
        atime = t
        count += 1
        s += "\n|  %2d. step: %.3f sec.: %s" % (i, duration, msg)
    return s + '\n' + ('-' * 80)

errordesc = {
    "badArgument": "The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.",
    "badResumptionToken": "The value of the resumptionToken argument is invalid or expired.",
    "badVerb": "none or no valid OAI verb",
    "cannotDisseminateFormat": "The metadata format identified by the value given for the metadataPrefix argument is not supported by the item or by the repository.",
    "idDoesNotExist": "The value of the identifier argument is unknown or illegal in this repository.",
    "noRecordsMatch": "The combination of the values of the from, until, set and metadataPrefix arguments results in an empty list.",
    "noMetadataFormats": "There are no metadata formats available for the specified item.",
    "noSetHierarchy": "The repository does not support sets.",
    "noPermission": "The requested records are protected",
    "badDateformatUntil": "Bad argument (until): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
    "badDateformatFrom": "Bad argument (from): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
}


def mklink(req):
    return "http://" + config.get("host.name", socket.gethostname() + ":8081") + "/oai/oai"


def writeHead(req, attributes=""):
    request = mklink(req)
    d = ISO8601(date.now())
    try:
        verb = req.params["verb"]
    except KeyError:
        verb = ""
    req.reply_headers['charset'] = 'utf-8'
    req.reply_headers['Content-Type'] = 'text/xml; charset=utf-8'
    req.write("""<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
        <responseDate>%sZ</responseDate>
        <request""" % (ISO8601(date.now())))
    if attributes != "noatt":
        for n in ["verb", "identifier", "metadataprefix", "from", "until", "set"]:
            if n in req.params:
                req.write(' %s="%s"' % (n, esc(req.params[n])))
    req.write('>%s</request>' % (request))
    if DEBUG:
        timetable_update(req, "leaving writeHead")


def writeTail(req):
    req.write('</OAI-PMH>')
    if DEBUG:
        timetable_update(req, "leaving writeTail")


def writeError(req, code, detail=""):
    if "verb" not in req.params:
        verb = ""

    if detail != "":
        desc = errordesc[detail]
    else:
        desc = errordesc[code]
    req.write('<error code="%s">%s</error>' % (code, desc))
    logg.info("%s:%d OAI (error code: %s) %s", req.ip, req.channel.addr[1], (code), (req.path + req.uri).replace('//', '/'))


def ISO8601(t=None):
    # MET summer time
    if not t:
        t = date.now()
    return "%0.4d-%0.2d-%0.2dT%0.2d:%0.2d:%0.2d" % (t.year, t.month, t.day, t.hour, t.minute, t.second)


def parseDate(string):
    if string.endswith("Z"):
        string = string[:-1]
    try:
        return date.parse_date(string, "%Y-%m-%d")
    except:
        try:
            return date.parse_date(string, "%Y-%m-%dT%H:%M:%S")
        except:
            return date.parse_date(string[12:], "%Y-%m-%d")


def checkParams(req, list):
    params = req.params.copy()
    for entry in list:
        if entry not in params:
            return 0
        del params[entry]
    if len(params) > 0:
        return 0
    return 1


def getExportMasks(regexp):
    exportmasks = q(Node).filter(Node.a.masktype == 'export').all()
    exportmasks = [(n, n.name) for n in exportmasks if re.match(regexp, n.name) and n.type == 'mask']
    dict_metadatatype2exportmask = {}
    for exportmask in exportmasks:
        parents = exportmask[0].parents
        try:
            mdt_node = [p for p in parents if p.type == 'metadatatype'][0]
            mdt = (mdt_node, mdt_node.name)
            dict_metadatatype2exportmask[mdt] = dict_metadatatype2exportmask.setdefault(mdt, []) + [exportmask]
        except:
            pass
    return dict_metadatatype2exportmask.items()


def getOAIExportFormatsForSchema(schema_name):
    try:
        schema_node = [x for x in q(Metadatatypes).one().children if x.name == schema_name][0]
        res = [x.name for x in schema_node.children if (x.type == 'mask' and x.get('masktype') == 'export')]
        return [x.replace('oai_', '', 1) for x in res if x.startswith('oai_')]
    except:
        logg.exception("ERROR in getOAIExportMasksForSchema('%s')", schema_name)
        return []


def nodeHasOAIExportMask(node, metadataformat):
    if node.getSchema() in [x[0][1] for x in getExportMasks('oai_%s$' % metadataformat)]:
        return True
    return False


def get_schemata_for_metadataformat(metadataformat):
    mdt_masks_list = getExportMasks("oai_" + metadataformat.lower() + "$")  # check exact name
    schemata = [x[0][1] for x in mdt_masks_list if x[1]]
    return schemata


def ListMetadataFormats(req):
    if "set" in req.params:
        return writeError(req, "badArgument")

    # supported oai metadata formats are configured in section
    # oai.formats in the mediatum.cfg file
    d = config.getsubset('oai')
    formats = [x.strip() for x in d['formats'].split(',') if x.strip()]

    if "identifier" in req.params:
        # list only formats available for the given identifier
        try:
            nid = identifier2id(req.params.get("identifier"))
            if nid is None:
                return writeError(req, "idDoesNotExist")
            node = q(Node).get(nid)
        except (TypeError, KeyError):
            return writeError(req, "badArgument")
        if node is None:
            return writeError(req, "badArgument")

        if not node.has_read_access(user=get_guest_user()):
            return writeError(req, "noPermission")

        formats = [x for x in formats if nodeHasOAIExportMask(node, x.lower())]
        formats = [x for x in formats if filterFormat(node, x.lower())]

    # write xml for metadata formats list
    req.write('\n      <ListMetadataFormats>\n')
    for mdf in formats:
        try:
            req.write("""
             <metadataFormat>
               <metadataPrefix>%s</metadataPrefix>
               <schema>%s</schema>
               <metadataNamespace>%s</metadataNamespace>
             </metadataFormat>
             """ % (mdf, d["schema.%s" % mdf], d["namespace.%s" % mdf]))
        except:
            logg.exception("%s: OAI error reading oai metadata format %s from config file", __file__, mdf)
    req.write('\n</ListMetadataFormats>')
    if DEBUG:
        timetable_update(req, "leaving ListMetadataFormats")


def checkMetaDataFormat(format):
    d = config.getsubset('oai')
    try:
        return format.lower() in [x.strip().lower() for x in d['formats'].split(',') if x.strip()]
    except:
        return False


def Identify(req):
    if not checkParams(req, ["verb"]):
        return writeError(req, "badArgument")
    if config.get("config.oaibasename") == "":
        root = q(Root).one()
        name = root.getName()
    else:
        name = config.get("config.oaibasename")
    req.write("""
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
        </Identify>""" % (name, mklink(req), config.get("email.admin"), ustr(EARLIEST_YEAR - 1), config.get("host.name", socket.gethostname()), SAMPLE_IDENTIFIER))
    if DEBUG:
        timetable_update(req, "leaving Identify")


def getSetSpecsForNode(node):
    setspecs = oaisets.getSetSpecsForNode(node)
    setspecs_elements = ["<setSpec>%s</setSpec>" % setspec for setspec in setspecs]
    indent = '\n    '
    return indent + (indent.join(setspecs_elements))


def get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat):
    schema = getMetaType(schema_name)
    if schema:
        mask = schema.getMask(u"oai_" + metadataformat.lower())
    else:
        mask = None
    return mask


def writeRecord(req, node, metadataformat, mask=None):
    if not SET_LIST:
        initSetList(req)

    updatetime = node.get(DATEFIELD)
    if updatetime:
        d = ISO8601(date.parse_date(updatetime))
    else:
        d = ISO8601(date.DateTime(EARLIEST_YEAR - 1, 12, 31, 23, 59, 59))

    set_specs = getSetSpecsForNode(node)

    if DEBUG:
        timetable_update(req, " in writeRecord: getSetSpecsForNode: node: '%s, %s', metadataformat='%s' set_specs:%s" %
                         (ustr(node.id), node.type, metadataformat, ustr(set_specs)))

    record_str = """
           <record>
               <header><identifier>%s</identifier>
                       <datestamp>%sZ</datestamp>
                       %s
               </header>
               <metadata>""" % (mkIdentifier(node.id), d, set_specs)

    if DEBUG:
        timetable_update(req, " in writeRecord: writing header: node.id='%s', metadataformat='%s'" % (ustr(node.id), metadataformat))

    if metadataformat == "mediatum":
        record_str += core.xmlnode.getSingleNodeXML(node)
    # in [masknode.name for masknode in getMetaType(node.getSchema()).getMasks() if masknode.get('masktype')=='exportmask']:

    #elif nodeHasOAIExportMask(node, metadataformat.lower()):
    #    mask = getMetaType(node.getSchema()).getMask(u"oai_" + metadataformat.lower())
    elif mask:
        if DEBUG:
            timetable_update(
                req,
                """ in writeRecord: mask = getMetaType(node.getSchema()).getMask(u"oai_"+metadataformat.lower()): node.id='%s', metadataformat='%s'""" %
                (ustr(
                    node.id),
                    metadataformat))
        # XXX: fixXMLString is gone, do we need to sanitize XML here?
        record_str += mask.getViewHTML([node], flags=8).replace('lang=""', 'lang="unknown"')  # for testing only, remove!
        if DEBUG:
            timetable_update(
                req,
                " in writeRecord: req.write(mask.getViewHTML([node], flags=8)): node.id='%s', metadataformat='%s'" %
                (ustr(
                    node.id),
                    metadataformat))

    else:
        record_str += '<recordHasNoXMLRepresentation/>'

    record_str += '</metadata></record>'

    req.write(record_str)

    if DEBUG:
        timetable_update(req, "leaving writeRecord: node.id='%s', metadataformat='%s'" % (ustr(node.id), metadataformat))


def mkIdentifier(id):
    return IDPREFIX + ustr(id)


def identifier2id(identifier):
    if identifier.startswith(IDPREFIX):
        nid = identifier[len(IDPREFIX):]
        # nid should be long int
        try:
            long(nid)
        except:
            nid = None
        return nid
    else:
        return None

# exclude children of media


def parentIsMedia(n):
    try:
        p = n.getParents()[0]
        return hasattr(p, "isContainer") and p.isContainer() == 0
    except IndexError:
        logg.exception("IndexError in export.oai.parentIsMedia(...) %s %s %s %s", n, n.id, n.type, n.name)
        return True


def retrieveNodes(req, setspec, date_from=None, date_to=None, metadataformat=None):
    schemata = []

    nodequery = None
    res = []

    if metadataformat == 'mediatum':
        metadatatypes = q(Metadatatypes).one().children
        schemata = [m.name for m in metadatatypes if m.type == 'metadatatype' and m.name not in ['directory', 'collection']]
    elif metadataformat:
        schemata = get_schemata_for_metadataformat(metadataformat)

    if DEBUG:
        timetable_update(req, "in retrieveNodes: find schemata with export mask for metadata type %s (%d found: '%s')" %
                         (metadataformat.lower(), len(schemata), ustr([x for x in schemata])))

    if setspec:
        nodequery = oaisets.getNodesQueryForSetSpec(setspec, schemata)
        # if for this oai group set no function is defined that retrieve the nodes query, use the filters
        if not nodequery:
            collections_root = q(Collections).one()
            nodequery = collections_root.all_children
            setspecFilter = oaisets.getNodesFilterForSetSpec(setspec, schemata)
            if schemata:
                nodequery = nodequery.filter(Node.schema.in_(schemata))
            if type(setspecFilter) == list:
                for sFilter in setspecFilter:
                    nodequery = nodequery.filter(sFilter)
            else:
                nodequery = nodequery.filter(setspecFilter)
    else:
        collections_root = q(Collections).one()
        nodequery = collections_root.all_children
        nodequery = nodequery.filter(Node.schema.in_(schemata))

    if DEBUG:
        timetable_update(req, "in retrieveNodes: after building NodeList for %d nodes" % (len(res)))

    if date_from:
        nodequery = nodequery.filter(Node.attrs[DATEFIELD].astext >= str(date_from))
        if DEBUG:
            timetable_update(req, "in retrieveNodes: after filtering date_from --> %d nodes" % (len(res)))
    if date_to:
        nodequery = nodequery.filter(Node.attrs[DATEFIELD].astext <= str(date_to))
        if DEBUG:
            timetable_update(req, "in retrieveNodes: after filtering date_to --> %d nodes" % (len(res)))

    if nodequery:
        guest_user = get_guest_user()
        nodequery = nodequery.filter_read_access(user=guest_user)
    else:
        res = [n for n in res if n.has_read_access(user=get_guest_user())]
    if DEBUG:
        timetable_update(req, "in retrieveNodes: after read access filter --> %d nodes" % (len(res)))

    if not nodequery:
        collections = q(Collections).one()
        res = [n for n in res if isDescendantOf(n, collections)]
    if DEBUG:
        timetable_update(req, "in retrieveNodes: after checking descendance from basenode --> %d nodes" % (len(res)))

    # superflous ?!
    #if schemata:
    #    res = [n for n in res if n.getSchema() in schemata]
    #    if DEBUG:
    #        timetable_update(req, "in retrieveNodes: after schemata (%s) filter --> %d nodes" % (ustr(schemata), len(res)))

    if metadataformat and metadataformat.lower() in FORMAT_FILTERS.keys():
        format_string = metadataformat.lower()
        format_filter = FORMAT_FILTERS[format_string]['filterQuery']
        nodequery = nodequery.filter(format_filter)
        #res = [n for n in res if filterFormat(n, format_string)]
        if DEBUG:
            timetable_update(req, "in retrieveNodes: after format (%s) filter --> %d nodes" % (format_string, len(res)))

    if nodequery:
        res = nodequery

    return res


def new_token(req):
    token = ustr(random.random())
    with token_lock:
        # limit length to 32
        if len(tokenpositions) >= 32:
            tokenpositions.popitem(last=False)
        tokenpositions[token] = 0

    metadataformat = req.params.get("metadataPrefix", None)
    return token, metadataformat


def getNodes(req):
    global tokenpositions, CHUNKSIZE
    nodes = None
    nids = None

    if "resumptionToken" in req.params:
        token = req.params.get("resumptionToken")
        if token in tokenpositions:
            pos, nids, metadataformat = tokenpositions[token]
        else:
            return None, "badResumptionToken", None

        if not checkParams(req, ["verb", "resumptionToken"]):
            logg.info("OAI: getNodes: additional arguments (only verb and resumptionToken allowed)")
            return None, "badArgument", None
    else:
        token, metadataformat = new_token(req)
        if not checkMetaDataFormat(metadataformat):
            logg.info('OAI: ListRecords: metadataPrefix missing')
            return None, "badArgument", None
        pos = 0

    if not nids:
        string_from, string_to = None, None
        try:
            string_from = req.params["from"]
            date_from = parseDate(string_from)
            if date_from.year < EARLIEST_YEAR:
                date_from = date.DateTime(0, 0, 0, 0, 0, 0)
        except:
            if "from" in req.params:
                return None, "badArgument", None
            date_from = None

        try:
            date_to = parseDate(req.params["until"])
            string_to = req.params.get("until")
            if not date_to.has_time:
                date_to.hour = 23
                date_to.minute = 59
                date_to.second = 59
            if date_to.year < EARLIEST_YEAR - 1:
                raise
        except:
            if "until" in req.params:
                return None, "badArgument", None
            date_to = None

        setspec = None
        if "set" in req.params:
            setspec = req.params.get("set")
            if not oaisets.existsSetSpec(setspec):
                return None, "noRecordsMatch", None


        if string_from and string_to and (string_from > string_to or len(string_from) != len(string_to)):
            return None, "badArgument", None

        try:
            nodequery = retrieveNodes(req, setspec, date_from, date_to, metadataformat)
            nodequery = nodequery.filter(Node.subnode == False)  #[n for n in nodes if not parentIsMedia(n)]

            # filter out nodes that are inactive or older versions of other nodes
            #nodes = [n for n in nodes if n.isActiveVersion()]  # not needed anymore
        except:
            logg.exception('error retrieving nodes for oai')
            # collection doesn't exist
            return None, "badArgument", None
        #if not nodes:
        #    return None, "badArgument", None

    with token_lock:
        if not nids:
            import time
            from sqlalchemy.orm import load_only
            atime = time.time()
            nodes = nodequery.options(load_only('id')).all()
            etime = time.time()
            logg.info('querying %d nodes for tokenposition took %.3f sec.' % (len(nodes), etime - atime))
            atime = time.time()
            nids = [n.id for n in nodes]
            etime = time.time()
            logg.info('retrieving %d nids for tokenposition took %.3f sec.' % (len(nids), etime - atime))

        tokenpositions[token] = pos + CHUNKSIZE, nids, metadataformat


    tokenstring = '<resumptionToken expirationDate="' + ISO8601(date.now().add(3600 * 24)) + '" ' + \
        'completeListSize="' + ustr(len(nids)) + '" cursor="' + ustr(pos) + '">' + token + '</resumptionToken>'
    if pos + CHUNKSIZE >= len(nids):
        tokenstring = None
        with token_lock:
            del tokenpositions[token]
    logg.info("%s : set=%s, objects=%s, format=%s", req.params.get('verb'), req.params.get('set'), len(nids), metadataformat)
    res = nids[pos:pos + CHUNKSIZE]
    if DEBUG:
        timetable_update(req, "leaving getNodes: returning %d nodes, tokenstring='%s', metadataformat='%s'" %
                         (len(res), tokenstring, metadataformat))

    return res, tokenstring, metadataformat


def ListIdentifiers(req):
    if not SET_LIST:
        initSetList(req)

    nids, tokenstring, metadataformat = getNodes(req)

    if nids is None:
        return writeError(req, tokenstring)
    if not len(nids):
        return writeError(req, 'noRecordsMatch')
    nodes = q(Node).filter(Node.id.in_(nids)).all()

    req.write('<ListIdentifiers>')
    for n in nodes:
        updatetime = n.get(DATEFIELD)
        if updatetime:
            d = ISO8601(date.parse_date(updatetime))
        else:
            d = ISO8601()
        req.write('<header><identifier>%s</identifier><datestamp>%sZ</datestamp>%s\n</header>\n' %
                  (mkIdentifier(n.id), d, getSetSpecsForNode(n)))
    if tokenstring:
        req.write(tokenstring)
    req.write('</ListIdentifiers>')
    if DEBUG:
        timetable_update(req, "leaving ListIdentifiers")


def ListRecords(req):
    eyear = ustr(EARLIEST_YEAR - 1) + """-01-01T12:00:00Z"""
    if "until" in req.params.keys() and req.params.get("until") < eyear and len(req.params.get("until")) == len(eyear):
        return writeError(req, 'noRecordsMatch')
    if "resumptionToken" in req.params.keys() and "until" in req.params.keys():
        return writeError(req, 'badArgument')

    nids, tokenstring, metadataformat = getNodes(req)

    if nids is None:
        return writeError(req, tokenstring)
    if not len(nids):
        return writeError(req, 'noRecordsMatch')
    nodes = q(Node).filter(Node.id.in_(nids)).all()

    if nodes is None:
        return writeError(req, tokenstring)
    if not len(nodes):
        return writeError(req, 'noRecordsMatch')

    req.write('<ListRecords>')

    mask_cache_dict = {}
    for n in nodes:

        # retrieve mask from cache dict or insert
        schema_name = n.getSchema()
        look_up_key = u"%s_%s" % (schema_name, metadataformat)
        if look_up_key in mask_cache_dict:
            mask = mask_cache_dict.get(look_up_key)
        else:
            mask = get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat)
            if mask:
                mask_cache_dict[look_up_key] = mask

        try:
            writeRecord(req, n, metadataformat, mask=mask)
        except Exception as e:
            logg.exception("n.id=%s, n.type=%s, metadataformat=%s" % (n.id, n.type, metadataformat))
    if tokenstring:
        req.write(tokenstring)
    req.write('</ListRecords>')
    if DEBUG:
        timetable_update(req, "leaving ListRecords")


def GetRecord(req):
    if "identifier" in req.params:
        nid = identifier2id(req.params.get("identifier"))
        if nid is None:
            return writeError(req, "idDoesNotExist")
    else:
        return writeError(req, "badArgument")

    metadataformat = req.params.get("metadataPrefix", None)
    if not checkMetaDataFormat(metadataformat):
        return writeError(req, "badArgument")

    node = q(Node).get(nid)
    if node is None:
        return writeError(req, "idDoesNotExist")

    if metadataformat and (metadataformat.lower() in FORMAT_FILTERS.keys()) and not filterFormat(node, metadataformat.lower()):
        return writeError(req, "noPermission")

    if parentIsMedia(node):
        return writeError(req, "noPermission")

    if not node.has_read_access(user=get_guest_user()):
        return writeError(req, "noPermission")

    schema_name = node.getSchema()
    mask = get_oai_export_mask_for_schema_name_and_metadataformat(schema_name, metadataformat)

    req.write('<GetRecord>')
    writeRecord(req, node, metadataformat, mask=mask)
    req.write('</GetRecord>')
    if DEBUG:
        timetable_update(req, "leaving GetRecord")


def ListSets(req):
    # new container sets may have been added
    initSetList(req)
    req.write('\n<ListSets>')

    for setspec, setname in oaisets.getSets():
        req.write('\n <set><setSpec>%s</setSpec><setName>%s</setName></set>' % (setspec, setname))

    req.write('\n</ListSets>')
    if DEBUG:
        timetable_update(req, "leaving ListSets")


def initSetList(req=None):
    global SET_LIST

    oaisets.loadGroups()
    SET_LIST = oaisets.GROUPS
    logg.info('OAI: initSetList: found %s set groups: %s', len(SET_LIST), SET_LIST)

    if DEBUG:
        timetable_update(req, "leaving initSetList")


def oaiRequest(req):

    start_time = time.clock()
    req._tt = {'atime': now(), 'tlist': []}
    req.request["Content-Type"] = "text/xml"

    if "until" in req.params:
        try:
            date_to = parseDate(req.params.get("until"))
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatUntil")
            writeTail(req)
            return

    elif "from" in req.params:
        try:
            date_from = parseDate(req.params.get("from"))
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatFrom")
            writeTail(req)
            return

    if "verb" not in req.params:
        writeHead(req, "noatt")
        writeError(req, "badVerb")

    else:
        verb = req.params.get("verb")
        if verb == "Identify":
            writeHead(req)
            Identify(req)
        elif verb == "ListMetadataFormats":
            writeHead(req)
            ListMetadataFormats(req)
        elif verb == "ListSets":
            writeHead(req)
            ListSets(req)
        elif verb == "ListIdentifiers":
            writeHead(req)
            ListIdentifiers(req)
        elif verb == "ListRecords":
            writeHead(req)
            ListRecords(req)
        elif verb == "GetRecord":
            writeHead(req)
            GetRecord(req)
        else:
            writeHead(req, "noatt")
            writeError(req, "badVerb")

    writeTail(req)

    useragent = 'unknown'
    try:
        cutoff = 60
        useragent = req.request_headers['user-agent']
        if len(useragent) > cutoff:
            useragent = useragent[0:cutoff] + '...'
    except:
        pass

    exit_time = now()

    logg.info("%s:%d OAI (exit after %.3f sec.) %s - (user-agent: %s)",
              req.ip, req.channel.addr[1], (exit_time - start_time), (req.path + req.uri).replace('//', '/'), useragent)

    if DEBUG:
        logg.info(timetable_string(req))
