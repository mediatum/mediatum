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
import core.tree as tree
import socket
import random
import re
import time
import sys
import logging
import core.config as config
import core.users as users
import utils.date
from utils.dicts import MaxSizeDict
import utils.date as date
import core.acl as acl
import core.xmlnode
from utils.utils import esc,getCollection
from schema.schema import getMetaType

try:
    import json
except:
    import simplejson as json

    
DEBUG = False
DATEFIELD = "updatetime"
EARLIEST_YEAR = 1960
CHUNKSIZE = 10
IDPREFIX = "oai:mediatum2.ub.tum.org:node/"

tokenpositions = MaxSizeDict(32)

def OUT(msg, type="info"):
    if DEBUG:
        sys.stdout.flush()
    if type=="info":
        logging.getLogger('oai').info(msg)
    elif type=="error":
        logging.getLogger('oai').error(msg)
        

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
 "badDateformatUntil" : "Bad argument (until): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
 "badDateformatFrom" : "Bad argument (from): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
}


def mklink(req):
    return "http://"+config.get("host.name", socket.gethostname()+":8081")+"/oai/oai"

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
        <request""" %(ISO8601(date.now())))
    if attributes!="noatt":
        for n in ["verb", "identifier", "metadataprefix", "from", "until", "set"]:
            if n in req.params:
                req.write(' %s="%s"' %(n, esc(req.params[n])))
    req.write('>%s</request>' %(request))

def writeTail(req):
    req.write('</OAI-PMH>')

def writeError(req, code, detail=""):
    if not "verb" in req.params:
        verb = ""

    if detail!="":
        req.write('<error code="%s">%s</error>' %(code, errordesc[detail]))
    else:
        req.write('<error code="%s">%s</error>' %(code, errordesc[code]))
    OUT(code, 'error')

        
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
    if len(params)>0:
        return 0
    return 1

# FIXME: metadataformats are currently hardcoded- should depend on collection

def getExportMasks(regexp):
    exportmasks = [tree.getNode(nid) for nid in tree.getNodesByAttribute('masktype', 'export')]
    exportmasks = [(n, n.name) for n in exportmasks if re.match(regexp, n.name)]
    dict_metadatatype2exportmask = {}
    for exportmask in exportmasks:
        parents = exportmask[0].getParents()
        try:
            mdt_node = [p for p in parents if p.type == 'metadatatype'][0]
            mdt = (mdt_node, mdt_node.name)
            dict_metadatatype2exportmask[mdt] = dict_metadatatype2exportmask.setdefault(mdt, []) + [exportmask]
        except:
            pass
    return dict_metadatatype2exportmask.items()

def getOAIExportFormatsForSchema(schema_name):
    try:
        schema_node = [x for x in tree.getRoot('metadatatypes').getChildren() if x.name==schema_name][0]
        res = [x.name for x in schema_node.getChildren() if (x.type=='mask' and x.get('masktype')=='export')]
        return [x.replace('oai_','',1) for x in res if x.startswith('oai_')]
    except:
        OUT("ERROR in getOAIExportMasksForSchema('%s'):\n%s %s" % (schema_name, str(sys.exc_info()[0]), str(sys.exc_info()[1])), 'error')
        return []

def getOAIExportFormatsForIdentifier(identifier):
    nid = identifier2id(identifier)
    try:
        node = tree.getNode(nid)
    except:
        return []
    return getOAIExportFormatsForSchema(node.getSchema())


def nodeHasOAIExportMask(node, metadataformat):
    mdt2ems = getExportMasks('oai_%s$' % metadataformat)
    if node.getSchema() in [x[0][1] for x in mdt2ems]:
        return True
    return False

def ListMetadataFormats(req):
    d = config.getsubset('oai')

    formats = [x.strip() for x in d['formats'].split(',') if x.strip()]

    if "identifier" in req.params:
        nid = identifier2id(req.params.get("identifier"))
        try:
            node = tree.getNode(nid)
        except (TypeError, KeyError, tree.NoSuchNodeError):
            return writeError(req,"badArgument")

        access = acl.AccessData(req)    
        if not access.hasReadAccess(node):
            return writeError(req, "noPermission")    
        formats = [x for x in formats if nodeHasOAIExportMask(node, x.lower())]
    elif "set" in req.params:
        set_type = None
        setspec = req.params["set"]
        if setspec:
            if setspec.decode().isdecimal():
                try:
                    col = tree.getNode(setspec)
                except (TypeError, KeyError, tree.NoSuchNodeError):
                    return writeError(req,"badArgument")
                
                col_formats = [x.strip().lower() for x in col.get('oai.formats').split(',') if x.strip()]
                formats = [x for x in formats if x.lower() in col_formats]
                set_type = 'container'
            else:
                d_specs = getOAIConfigSpecs()
                for key in d_specs:
                    d_spec = d_specs[key]
                    if d_spec['spec'] == setspec:
                        set_type = 'virtual'
                        break
                spec_formats = []
                for spec_type in d_spec['types']:
                    schema_name = spec_type['schema']
                    spec_formats += getOAIExportFormatsForSchema(schema_name)
                spec_formats = list(set(spec_formats))
                formats = [x for x in formats if x.lower() in spec_formats]

                if not set_type:
                    return writeError(req,"badArgument")

    req.write('\n      <ListMetadataFormats>\n')

    for mdf in formats:
        try:
            req.write("""
             <metadataFormat>
                 <metadataPrefix>%s</metadataPrefix>
                 <schema>%s</schema>
                 <metadataNamespace>%s</metadataNamespace>
             </metadataFormat>
             """ % (mdf, d["schema.%s" % mdf], d["namespace.%s" % mdf]) )
        except:
            OUT("%s: OAI error reading oai metadata format %s from config file" % (__file__, mdf), 'error')
    req.write('\n</ListMetadataFormats>')


def checkMetaDataFormat(format):
    d = config.getsubset('oai')
    try:
        return format.lower() in [x.strip().lower() for x in d['formats'].split(',') if x.strip()]
    except:
        return False

def Identify(req):
    if not checkParams(req, ["verb"]):
        return writeError(req, 'Identify: verb missing')
    root = tree.getRoot()
    if config.get("config.oaibasename")=="":
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
       </Identify>""" %(name, mklink(req), config.get("email.admin"), str(EARLIEST_YEAR-1)))


def writeRecord(req, node, metadataformat):
    collection = getCollection(node)
    updatetime = node.get(DATEFIELD)
    if updatetime:
        d = ISO8601(date.parse_date(updatetime))
    else:
        d = ISO8601(date.DateTime(EARLIEST_YEAR-1,12,31,23,59,59))

    req.write("""
           <record>
               <header><identifier>%s</identifier>
                       <datestamp>%sZ</datestamp>
                       <setSpec>%s</setSpec>
               </header>
               <metadata>""" %(mkIdentifier(node.id), d, collection.id))

    if metadataformat=="mediatum":
        req.write(core.xmlnode.getSingleNodeXML(node))
    elif nodeHasOAIExportMask(node, metadataformat.lower()): # in [masknode.name for masknode in getMetaType(node.getSchema()).getMasks() if masknode.get('masktype')=='exportmask']:
        mask = getMetaType(node.getSchema()).getMask("oai_"+metadataformat.lower())
        req.write(mask.getViewHTML([node], flags=8))
    else:
        req.write('<recordHasNoXMLRepresentation/>')

    req.write('</metadata></record>')


def mkIdentifier(id):
    return IDPREFIX+id

def identifier2id(id):
    if id.startswith(IDPREFIX):
        return id[len(IDPREFIX):]
    else:
        return id

def getOAIConfigSpecs():
    d_specs = {}
    d = config.getsubset('oai')
    for oai_set in [x.strip() for x in d['sets'].split(',') if x.strip()]:
        #if 1:
        struct = json.loads(d["set."+oai_set])
        d_specs[oai_set] = struct
    return d_specs

def retrieveNodes(access, setspec, date_from=None, date_to=None, metadataformat=None):
    query_descriptors = []
    set_type = 'container'

    if metadataformat:
        mdt_masks_list = getExportMasks("oai_"+metadataformat.lower()+"$") # check exact name
        schemata = [x[0][1] for x in mdt_masks_list if x[1]]

    #set_type = None # 'container' (collections, collection or directory), 'virtual' (configured in mediatum.cfg)
    if setspec:
        if setspec.decode().isdecimal():
            collection = tree.getNode(setspec)
        else:
            d_specs = getOAIConfigSpecs()
            for key in d_specs:
                d_spec = d_specs[key]
                if d_spec['spec'] == setspec:
                    set_type = 'virtual'
                    break
            if not set_type:
                return []
    else:
        collection = tree.getRoot("collections")
        collectionid = collection.id
        
    if set_type=='container':
        for schema in schemata:
            query_descriptors.append( (schema, collection, []) )
    
    elif set_type=='virtual':
        configured_schemata = []
        for configured_type in d_spec['types']:
            if not configured_type['schema'] in schemata:
                OUT('oai export mask missing for schema %s' % (configured_type['schema']), 'error')
                continue

            if 'base_node' in configured_type.keys():
                try:
                    collection = tree.getNode(configured_type['base_node'])
                except:
                    OUT('oai base_node %s missing' % (configured_type['basenode']), 'error')
                    continue
            else:
                collection = tree.getRoot("collections")

            query_descriptors.append( (configured_type['schema'], collection, configured_type['attributes']) )

    def concatNodeLists(nodelist1, nodelist2):
        return tree.NodeList(list(set(nodelist1.getIDs() + nodelist2.getIDs())))

    res = tree.NodeList([])
    for schema, collection, attribute_items in query_descriptors:
        query = "schema=" + schema

        for attribute_item in attribute_items:
            query += ' and %s="%s"' % (attribute_item[0], attribute_item[1])

        if date_from:
            if query:
                query += " and "
            query += DATEFIELD + " >= "+str(date_from)

        if date_to:
            if query:
                query += " and "
            query += DATEFIELD + " <= "+str(date_to)
        nodes = collection.search(query)

        if access:
            nodes = access.filter(nodes)

        res = concatNodeLists(res, nodes)
        sys.stdout.flush()

    return res

def getNodes(req):
    global tokenpositions,CHUNKSIZE
    access = acl.AccessData(req)
    nodes = None

    if "resumptionToken" in req.params:
        token = req.params.get("resumptionToken")
        if token in tokenpositions:
            pos, nodes, metadataformat = tokenpositions[token]
        else:
            return None, "badResumptionToken", None

        if not checkParams(req, ["verb", "resumptionToken"]):
            OUT("getNodes: additional arguments (only verb and resumptionToken allowed)")
            return None, "badArgument", None

    else:
        token = str(random.random())
        tokenpositions[token] = pos = 0

        metadataformat = req.params.get("metadataPrefix", None)
        if not checkMetaDataFormat(metadataformat):
            OUT('ListRecords: metadataPrefix missing', 'error')
            return None, "badArgument", None

    if not nodes:
        string_from, string_to = None, None
        try:
            string_from = req.params["from"]
            date_from = parseDate(string_from)
            if date_from.year<EARLIEST_YEAR:
                date_from=date.DateTime(0,0,0,0,0,0)
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
            if date_to.year<EARLIEST_YEAR-1:
                raise
        except:
            if "until" in req.params:
                return None,"badArgument",None
            date_to = None

        setspec = None
        if "set" in req.params:
            setspec = req.params.get("set")
        
        if string_from and string_to and (string_from > string_to or len(string_from) != len(string_to)):
            return None, "badArgument", None

        try:
            nodes = retrieveNodes(access, setspec, date_from, date_to, metadataformat)
        except tree.NoSuchNodeError:
            # collection doesn't exist
            return None, "badArgument", None

    tokenpositions[token] = pos + CHUNKSIZE, nodes, metadataformat

    tokenstring = '<resumptionToken expirationDate="'+ISO8601(date.now().add(3600*24))+'" '+ \
                   'completeListSize="'+str(len(nodes))+'" cursor="'+str(pos)+'">'+token+'</resumptionToken>'
    if pos + CHUNKSIZE>=len(nodes):
        tokenstring = None
        del tokenpositions[token]
    OUT(req.params.get('verb')+": set="+str(req.params.get('set'))+", "+ str(len(nodes))+" objects, format="+metadataformat)
    return tree.NodeList(nodes[pos:pos+CHUNKSIZE]), tokenstring, metadataformat

def ListIdentifiers(req):
    nodes, tokenstring, metadataformat = getNodes(req)
    if nodes is None:
        return writeError(req,tokenstring)
    if not len(nodes):
        return writeError(req,'noRecordsMatch')

    req.write('<ListIdentifiers>')
    for n in nodes:
        updatetime = n.get(DATEFIELD)
        if updatetime:
            d = ISO8601(date.parse_date(updatetime))
        else:
            d = ISO8601()
        req.write('<header><identifier>%s</identifier><datestamp>%sZ</datestamp></header>\n' %(mkIdentifier(n.id), d))
    if tokenstring:
        req.write(tokenstring)
    req.write('</ListIdentifiers>')


def ListRecords(req):
    eyear = str(EARLIEST_YEAR-1)+"""-01-01T12:00:00Z"""
    if "until" in req.params.keys() and req.params.get("until")<eyear and len(req.params.get("until"))==len(eyear):
        return writeError(req, 'noRecordsMatch')
    if "resumptionToken" in req.params.keys() and "until" in req.params.keys():
        return writeError(req, 'badArgument')

    nodes, tokenstring, metadataformat = getNodes(req)
    if nodes is None:
        return writeError(req,tokenstring)
    if not len(nodes):
        return writeError(req,'noRecordsMatch')

    req.write('<ListRecords>')
    for n in nodes:
        writeRecord(req, n, metadataformat)
    if tokenstring:
        req.write(tokenstring)
    req.write('</ListRecords>')


def GetRecord(req):
    access = acl.AccessData(req)
    if "identifier" in req.params:
        id = identifier2id(req.params.get("identifier"))
    else:
        return writeError(req,"badArgument")

    metadataformat = req.params.get("metadataPrefix",None)
    if not checkMetaDataFormat(metadataformat):
        return writeError(req,"badArgument")

    try:
        node = tree.getNode(id)
    except (TypeError, KeyError, tree.NoSuchNodeError):
        return writeError(req, "idDoesNotExist")

    if not access.hasReadAccess(node):
        return writeError(req,"noPermission")

    req.write('<GetRecord>')
    writeRecord(req, node, metadataformat)
    req.write('</GetRecord>')

def ListSets(req):
    access = acl.AccessData(req)
    node_list = tree.NodeList(tree.getNodesByAttribute('oai.setname', '*'))
    node_list = node_list.sort(field="oai.setname", direction="down")

    node_list = [node for node in node_list if node.type in ['collection', 'directory']]
    node_list = [node for node in node_list if node.get('oai.setname').strip()]
    node_list = [node for node in node_list if node.get('oai.formats').strip()]

    node_list = access.filter(node_list, accesstype="read")

    req.write('\n<ListSets>')
    # sets configured by container node attributes
    for node in node_list:
        req.write('\n <set><setSpec>%s</setSpec><setName>%s</setName></set>' %(node.id, exc(node.get('oai.setname'))))
    
    # sets configured in mediatum.cfg [oai]
    d = config.getsubset('oai')
    oai_sets = []
    if 'sets' in d:
        oai_sets = [x.strip() for x in d['sets'].split(',') if x.strip()]
        for oai_set in oai_sets:
            if 1:
                struct = json.loads(d["set."+oai_set])
                for mdt in struct['types']:
                    for attr_name, attr_value in mdt['attributes']:
                        pass
                req.write('\n <set><setSpec>%s</setSpec><setName>%s</setName></set>' %(struct['spec'], esc(struct['name'])))

            if 0:
                OUT('error loading oai set parameters from config for oai set: %s' %(str(oai_set)), 'error')
    req.write('\n</ListSets>')
    OUT('ListSets: found %s sets' %(len(oai_sets)))

def oaiRequest(req):
    req.request["Content-Type"] = "text/xml"

    if "until" in req.params:
        try:
            date_to = parseDate(req.params["until"])
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatUntil")
            writeTail(req)
            return

    elif "from" in req.params:
        try:
            date_from = parseDate(req.params["from"])
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatFrom")
            writeTail(req)
            return

    if "verb" not in req.params:
        writeHead(req, "noatt")
        writeError(req,"badVerb")

    else:
        verb = req.params["verb"]
        if verb=="Identify":
            writeHead(req)
            Identify(req)
        elif verb=="ListMetadataFormats":
            writeHead(req)
            ListMetadataFormats(req)
        elif verb=="ListSets":
            writeHead(req)
            ListSets(req)
        elif verb=="ListIdentifiers":
            writeHead(req)
            ListIdentifiers(req)
        elif verb=="ListRecords":
            writeHead(req)
            ListRecords(req)
        elif verb=="GetRecord":
            writeHead(req)
            GetRecord(req)
        else:
            writeHead(req, "noatt")
            writeError(req,"badVerb")

    writeTail(req)

